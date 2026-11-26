"""Link raw media, source documents and declared claims to the locked timeline."""

from pathlib import Path
import math
import re
from typing import Any

from common import read_json, sha256_file, write_json


def import_sources(path: Path, pipeline_dir: Path) -> None:
    manifest = read_json(path)
    for source in manifest.get("sources", []):
        file = (path.resolve().parent / source["path"]).resolve()
        source["path"] = str(file)
        if not source.get("sha256") and file.is_file():
            source["sha256"] = sha256_file(file)
    write_json(pipeline_dir / "00_sources.json", manifest)


def _range(start: Any, end: Any) -> list[float] | None:
    try:
        start_sec, end_sec = float(start), float(end)
    except (ValueError, TypeError):
        return None
    return [start_sec, end_sec] if 0 <= start_sec < end_sec and math.isfinite(end_sec) else None


def _valid_locator(locator: str) -> bool:
    if re.fullmatch(r"(page|row|line|csv):[1-9][0-9]*", locator):
        return True
    if locator == "asset" or locator.startswith("json:/"):
        return True
    if locator.startswith("time:"):
        return bool(_range(*locator[5:].split("-", 1))) if "-" in locator else False
    return False


def write_source_review(pipeline_dir: Path) -> dict[str, Any]:
    def read(name: str) -> dict[str, Any]:
        path = pipeline_dir / name
        return read_json(path) if path.is_file() else {}

    manifest = read("01_manifest.json")
    timeline = read("04_edl.json")
    audio = read("03_audio_events.json")
    spec = read("00_code_spec.json")
    intel = read("00_raw_intel.json")
    declarations = read("00_sources.json")

    digests: dict[str, str | None] = {}

    def digest(file_name: str) -> str | None:
        if not file_name:
            return None
        if file_name not in digests:
            file = Path(file_name)
            digests[file_name] = sha256_file(file) if file.is_file() else None
        return digests[file_name]

    media: dict[str, dict[str, Any]] = {}
    for item in manifest.get("items", []):
        mp = item.get("normalized_mp4")
        if mp:
            media[str(mp)] = item
            try:
                media[str(Path(mp).resolve())] = item
            except Exception:
                pass

    def media_ref(media_path: str | None, start: Any, end: Any) -> dict[str, Any] | None:
        if not media_path:
            return None
        item = media.get(media_path) or {}
        if not item:
            try:
                item = media.get(str(Path(media_path).resolve()), {})
            except Exception:
                item = {}
        source = str(item.get("source_path") or media_path)
        generated = bool(item.get("source_is_code_scene")) or not item
        return {
            "path": source,
            "sha256": digest(source),
            "range_sec": _range(start, end),
            "origin": "generated" if generated else "original",
        }

    shots = []
    for clip in timeline.get("clips", []):
        shots.append({
            "clip_id": clip["clip_id"], "sentence_id": clip.get("sentence_id"), "purpose": clip.get("purpose"),
            "timeline_sec": _range(clip.get("timeline_in_sec"), clip.get("timeline_out_sec")),
            "picture": media_ref(clip.get("media_path"), clip.get("source_in_sec"), clip.get("source_out_sec")),
        })
    tts_wav_p = pipeline_dir / "02_tts_voice.wav"
    narration = {}
    for sent in audio.get("sentences", []):
        timeline_sec = _range(sent.get("start_sec"), sent.get("end_sec"))
        voice = media_ref(sent.get("source_media"), sent.get("source_in_sec"), sent.get("source_out_sec"))
        if sent.get("voice_source"):
            original_offset = float(sent.get("voice_source_offset_sec") or 0)
            s_in = sent.get("source_in_sec")
            s_out = sent.get("source_out_sec")
            rng = (
                _range(max(0.0, float(s_in) - original_offset), float(s_out) - original_offset)
                if s_in is not None and s_out is not None
                else timeline_sec
            )
            voice = {
                "path": sent["voice_source"], "sha256": digest(sent["voice_source"]), "origin": "original",
                "range_sec": rng,
            }
        elif voice is None and tts_wav_p.is_file():
            voice = {
                "path": str(tts_wav_p.resolve()),
                "sha256": digest(str(tts_wav_p.resolve())),
                "origin": "generated",
                "range_sec": _range(sent.get("source_in_sec"), sent.get("source_out_sec")) or timeline_sec,
            }
        narration[sent["id"]] = {
            "sentence_id": sent["id"], "text": sent.get("text"), "spoken_text": sent.get("say_text"),
            "timeline_sec": timeline_sec,
            "voice": voice,
            "overlapping_clips": [
                item["clip_id"] for item in shots
                if timeline_sec and item["timeline_sec"] and
                max(timeline_sec[0], item["timeline_sec"][0]) < min(timeline_sec[1], item["timeline_sec"][1])
            ],
        }

    sources = {str(source["id"]): source for source in declarations.get("sources", [])}
    for source in intel.get("proof_assets", []):
        if source.get("id"):
            sources.setdefault(source["id"], source)
    for row in intel.get("source_utterances", []):
        sources.setdefault(row["id"], {"path": row["source_path"], "sha256": row["source_sha256"], "locator": row["locator"]})

    claims = list(declarations.get("claims", []))
    claims.extend({
        **fact,
        "id": fact.get("id") or f"fact_{index:03d}",
        "text": fact.get("text") or fact.get("value"),
    } for index, fact in enumerate(spec.get("facts", []), 1))
    subs_data = read("05_subtitles.json")
    pkg_data = read("06_packaging.json")
    fps = float(timeline.get("fps") or 30.0)
    on_screen_timed: list[tuple[str, list[float] | None]] = [
        (str(line), None) for line in spec.get("exact_copy", [])
    ]
    for element in pkg_data.get("visual_elements", []):
        elem_txt = str(element.get("text_or_asset") or "")
        sf = element.get("start_frame")
        ef = element.get("end_frame")
        tr = _range(sf / float(fps), ef / float(fps)) if (sf is not None and ef is not None) else None
        on_screen_timed.append((elem_txt, tr))
    for sub in subs_data.get("entries", []):
        if sub.get("suppressed"):
            continue
        on_screen_timed.append((str(sub.get("text") or ""), _range(sub.get("start_sec"), sub.get("end_sec"))))

    checked = []
    for index, claim in enumerate(claims, 1):
        text = str(claim.get("text") or "")
        target = narration.get(str(claim.get("sentence_id")))
        requested_clip = claim.get("clip_id")
        shot = next((s for s in shots if s["clip_id"] == requested_clip), None) if requested_clip else None
        if target is not None:
            matched = bool(text and any(text in str(target.get(key) or "") for key in ("text", "spoken_text")))
        else:
            if not claim.get("sentence_id") and text:
                if shot and shot.get("timeline_sec"):
                    s0, s1 = shot["timeline_sec"]
                    matched = any(
                        text in line and (tr is None or max(s0, tr[0]) < min(s1, tr[1]))
                        for line, tr in on_screen_timed
                    )
                else:
                    matched = any(text in line for line, _ in on_screen_timed)
            else:
                matched = False
        clips = target["overlapping_clips"] if target else []
        if requested_clip:
            matched = matched and shot is not None and (target is None or requested_clip in clips)
            if shot:
                clips = [requested_clip]
        references = []
        citations = claim.get("citations") or ([claim] if claim.get("source_id") else [])
        for citation in citations:
            source = sources.get(str(citation.get("source_id")), {})
            locator = str(citation.get("locator") or source.get("locator") or "")
            file_name = str(source.get("path") or "")
            current_hash = digest(file_name)
            references.append({
                "source_id": citation.get("source_id"), "path": file_name, "locator": locator,
                "sha256": source.get("sha256"),
                "valid": bool(current_hash and current_hash == source.get("sha256") and _valid_locator(locator)),
            })
        checked.append({
            "id": claim.get("id") or f"claim_{index:03d}", "text": text, "sentence_id": claim.get("sentence_id"),
            "timeline_sec": target["timeline_sec"] if target else next(
                (s["timeline_sec"] for s in shots if s["clip_id"] == requested_clip), None
            ),
            "clip_ids": clips, "source_refs": references,
            "status": "PENDING_REVIEW" if matched and references and all(ref["valid"] for ref in references) else "UNRESOLVED",
        })

    receipt = {"shots": shots, "narration": list(narration.values()), "claims": checked}
    write_json(pipeline_dir / "04_source_review.json", receipt)
    return receipt


def source_review_status(report: dict[str, Any]) -> str:
    claims = report.get("claims", [])
    if not claims:
        return "NOT_REQUESTED"
    hash_cache: dict[str, str | None] = {}
    for claim in claims:
        if claim["status"] == "UNRESOLVED" or not claim.get("source_refs"):
            return "FAIL"
        for ref in claim["source_refs"]:
            p_str = str(ref["path"])
            if p_str not in hash_cache:
                source = Path(p_str)
                hash_cache[p_str] = sha256_file(source) if source.is_file() else None
            if not hash_cache[p_str] or hash_cache[p_str] != ref["sha256"]:
                return "FAIL"
    return "PENDING_REVIEW"
