"""Resolve a vehicle name against the installed War Thunder catalog.

Only status='resolved' authorizes using exact_id. Exact names resolve unless they
name more than one distinct ground-vehicle model; fuzzy candidates always need a
variant choice. The installed game is read only; compact/cache files are written
under --project/cache. --catalog-json reads a fixture without native dependencies.
"""
from __future__ import annotations

import argparse
import contextlib
from difflib import SequenceMatcher
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import unicodedata

SCHEMA_VERSION = 1
PINNED_EXPORTER_COMMIT = "99c794ab102785c39e628033a09bf4ff18dbe64e"
DEFAULT_GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\War Thunder")
# In-game/colloquial names that differ from the catalog display name. Keys are
# normalize(query) without spaces; a target only counts if the ID exists.
ALIASES = {
    "bmpt72": "ussr_bmpt_72", "terminator2": "ussr_bmpt_72",
    "pantsirs1": "ussr_pantsyr_s1", "pantsyrs1": "ussr_pantsyr_s1",
    "sturmtiger": "germ_sturmmorser_sturmtiger", "sturmmorser": "germ_sturmmorser_sturmtiger",
    "38cmsturmmorser": "germ_sturmmorser_sturmtiger", "38cmrw61": "germ_sturmmorser_sturmtiger",
    "elephant": "germ_panzerjager_tiger_p_elefant",
    "kingtiger": "germ_pzkpfw_vi_ausf_b_tiger_iih", "konigstiger": "germ_pzkpfw_vi_ausf_b_tiger_iih",
    "tiger2": "germ_pzkpfw_vi_ausf_b_tiger_iih",
}
GROUND_TYPES = {"tanks"}
# Leading WT name glyphs mark foreign copies, squadron, event or premium
# variants (e.g. U+2417 China copy, U+2420 event, U+25CD squadron).
DECORATION = re.compile(r"^[^\w\s(\[\"']+", re.UNICODE)
_QT_APP = None
_DLL_HANDLES = []


def normalize(value):
    value = unicodedata.normalize("NFKD", str(value)).casefold()
    value = "".join(c for c in value if not unicodedata.combining(c))
    value = re.sub(r"(?<=[^\W\d_])(?=\d)|(?<=\d)(?=[^\W\d_])", " ", value)
    return " ".join(re.findall(r"[^\W_]+", value, re.UNICODE))


def validate_query(query):
    query = query.strip()
    if not query or len(query) > 160:
        raise ValueError("Query must contain 1 to 160 characters")
    if (any(unicodedata.category(c).startswith("C") for c in query)
            or any(c in query for c in "\\;|&$`<>:") or ".." in query
            or query.startswith("/") or not any(c.isalnum() for c in query)):
        raise ValueError("Expected a vehicle name or catalog ID, not a path or command")
    return query


def normalize_catalog(payload):
    rows = payload.get("vehicles") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise ValueError("Catalog JSON must be a list or an object containing vehicles[]")
    unique = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Each catalog vehicle must be an object")
        vehicle_id = str(row.get("id", "")).strip().casefold()
        if not re.fullmatch(r"[a-z0-9][a-z0-9_.-]*", vehicle_id) or ".." in vehicle_id:
            raise ValueError("Catalog contains an invalid vehicle ID")
        premium = row.get("premium", row.get("is_premium"))
        explicit_premium = isinstance(premium, bool)
        vehicle = {
            "id": vehicle_id, "name": str(row.get("name") or vehicle_id),
            "nation": row.get("nation"), "type": row.get("type", row.get("vehicle_type")),
            "model_id": row.get("model_id"),
            "premium": premium if explicit_premium else None,
            "premium_status": "catalog_verified" if explicit_premium else "unverified",
        }
        if vehicle_id in unique and unique[vehicle_id] != vehicle:
            raise ValueError(f"Conflicting catalog records for {vehicle_id}")
        unique[vehicle_id] = vehicle
    return sorted(unique.values(), key=lambda row: row["id"])


def is_ground(vehicle):
    """Unknown type (fixtures) stays plausible; known non-ground types do not."""
    kind = vehicle.get("type")
    return kind is None or str(kind).casefold() in GROUND_TYPES


def decorated(vehicle):
    return bool(DECORATION.match(vehicle["name"]))


def collapse_same_model(candidates, query):
    """Exact-name rows with one shared model print identically: keep one, list the rest.

    Preference: raw name equal to the query, then undecorated name, then ID.
    Rows without model_id cannot be proven equal and stay separate.
    """
    groups = {}
    for row in candidates:
        key = ("model", row["model_id"].casefold()) if row.get("model_id") else ("id", row["id"])
        groups.setdefault(key, []).append(row)
    result = []
    for rows in groups.values():
        rows = sorted(rows, key=lambda r: (r["name"].strip().casefold() != query.casefold(), decorated(r), r["id"]))
        best = dict(rows[0])
        if len(rows) > 1:
            best["equivalent_ids"] = [r["id"] for r in rows[1:]]
            best["match_reason"] += "_same_model"
        result.append(best)
    return sorted(result, key=lambda r: r["id"])


def resolve(query, vehicles, limit=12):
    """Return conservative ranked candidates; never promote fuzzy guesses.

    Only ground vehicles are plausible. An exact name or ID resolves unless it
    names more than one distinct ground-vehicle model; same-model copies in
    other nations are listed as equivalent_ids, longer-named family members as
    variants. Both are informational and never block resolution.
    """
    query = validate_query(query)
    norm = normalize(query)
    compact = norm.replace(" ", "")
    ground = [v for v in vehicles if is_ground(v)]
    result = {"schema_version": SCHEMA_VERSION, "query": query,
              "normalized_query": norm, "status": "no_match", "ambiguous": False,
              "exact_id": None, "requires_selection": False, "candidates": [],
              "candidate_count": 0, "truncated": False, "variants": [],
              "ignored_non_ground": sorted(v["id"] for v in vehicles if not is_ground(v)
                                           and (v["id"] == query.casefold() or normalize(v["name"]) == norm))}

    def finish(candidates, kind, may_resolve, variants=()):
        result["candidate_count"] = len(candidates)
        result["truncated"] = len(candidates) > limit
        result["match_kind"] = kind
        result["candidates"] = candidates[:limit]
        result["variants"] = [{"id": v["id"], "name": v["name"], "nation": v["nation"]} for v in variants][:limit]
        if len(candidates) == 1 and may_resolve:
            result.update(status="resolved", exact_id=candidates[0]["id"])
        elif candidates:
            result.update(status="ambiguous" if len(candidates) > 1 else "needs_confirmation",
                          ambiguous=len(candidates) > 1, requires_selection=True)
        return result

    def candidate(vehicle, score, reason):
        return {**vehicle, "score": round(score, 4), "match_reason": reason}

    exact = [candidate(v, 1.0, "exact_id") for v in ground if v["id"] == query.casefold()]
    if exact:
        # An explicit ground-vehicle ID is never second-guessed.
        return finish(exact, "exact_id", True)
    exact = collapse_same_model([candidate(v, 1.0, "exact_name") for v in ground
                                 if normalize(v["name"]) == norm], query)
    if exact:
        family = [candidate(v, .94, "longer_name_family_member") for v in ground
                  if normalize(v["name"]).startswith(norm + " ")]
        query_decorated = bool(DECORATION.match(query))
        if len(exact) > 1:
            # Distinct models share the name. A plain query means the plain
            # (main-nation) vehicle; a decorated query names its exact glyph.
            # Foreign copies/squadron/event variants are alternatives only.
            preferred = ([e for e in exact if e["name"].strip().casefold() == query.casefold()]
                         if query_decorated else [e for e in exact if not decorated(e)])
            if len(preferred) == 1:
                others = [e for e in exact if e is not preferred[0]]
                return finish(preferred, "exact_name_preferred_plain", True, variants=others+family)
            return finish(exact, "exact_name", False)
        # A bare family label can be only a decorated event/squadron vehicle's
        # name (the real catalog has an animal-version "Tiger"). If the user
        # did not type that glyph and plain family members exist, they most
        # likely mean the family: ask. Otherwise the exact name wins.
        if decorated(exact[0]) and not query_decorated and any(not decorated(f) for f in family):
            return finish(exact + family, "exact_name_with_variants", False)
        return finish(exact, "exact_name", True, variants=family)
    alias_id = ALIASES.get(compact)
    alias = [candidate(v, 1.0, "catalog_backed_alias") for v in vehicles if v["id"] == alias_id]
    if alias:
        return finish(alias, "alias", True)

    ranked = []
    tokens = set(norm.split())
    for vehicle in ground:
        fields = [normalize(vehicle["name"]), normalize(vehicle["id"]),
                  normalize(vehicle["model_id"] or "")]
        best = 0.0
        reason = "fuzzy_similarity"
        for field in fields:
            flattened = field.replace(" ", "")
            score = SequenceMatcher(None, compact, flattened).ratio()
            if tokens <= set(field.split()):
                score = max(score, .94 if field.startswith(norm) else .90)
                field_reason = "family_or_variant_terms"
            elif len(compact) >= 4 and compact in flattened:
                score = max(score, .86)
                field_reason = "partial_name"
            else:
                field_reason = "fuzzy_similarity"
            if score > best:
                best, reason = score, field_reason
        if best >= .64:
            ranked.append(candidate(vehicle, best, reason))
    ranked.sort(key=lambda v: (-v["score"], v["id"]))
    return finish(ranked, "fuzzy" if ranked else "none", False)


def project_child(project, path):
    resolved = path.resolve()
    if resolved == project or not resolved.is_relative_to(project):
        raise ValueError(f"Cache path escapes project: {path}")
    return resolved


def game_signature(game):
    files = {}
    for name in ("aces.vromfs.bin", "char.vromfs.bin", "lang.vromfs.bin"):
        path = game / name
        if not path.is_file():
            raise FileNotFoundError(f"Missing installed game data: {path}")
        stat = path.stat()
        files[name] = [stat.st_size, stat.st_mtime_ns]
    localizations = game / "lang"
    if localizations.is_dir():
        files["lang_csv"] = [[p.name, p.stat().st_size, p.stat().st_mtime_ns]
                             for p in sorted(localizations.glob("*.csv"))]
    return {"game_dir": str(game), "files": files,
            "exporter_commit": PINNED_EXPORTER_COMMIT}


def load_local_catalog(project, game, refresh=False):
    """Use the same pinned vendor/cache API as tools/export_vehicle.py."""
    global _QT_APP
    project, game = project.resolve(), game.resolve()
    signature = game_signature(game)
    cache_root = project_child(project, project / "cache" / "exporter")
    compact_root = project_child(project, project / "cache" / "vehicle_catalog")
    compact_path = project_child(project, compact_root / "vehicles.json")
    if compact_path.is_file() and not refresh:
        try:
            cached = json.loads(compact_path.read_text(encoding="utf-8"))
            if cached.get("schema_version") == SCHEMA_VERSION and cached.get("source_signature") == signature:
                return normalize_catalog(cached), {"kind": "project_json_cache", "path": str(compact_path),
                                                    "source_signature": signature}
        except (ValueError, TypeError, OSError):
            pass  # Rebuild a damaged/stale compact cache through the vendor API.
    vendor = project / "vendor" / "wt_asset_explorer"
    wt_ext = project / "vendor" / "wt_ext_cli-0.6.6" / "wt_ext_cli.exe"
    if not (vendor / "wtx" / "vehicles.py").is_file() or not wt_ext.is_file():
        raise FileNotFoundError("Pinned WT Asset Explorer/wt_ext_cli missing; prepare the project runtime first")
    # The extractor can prune obsolete generated subtrees. Validate every target
    # before handing it the isolated project cache; never point it at game data.
    for old in cache_root.glob("gamedata_*"):
        project_child(project, old)
        if old.is_symlink():
            raise ValueError(f"Unsafe generated cache link: {old}")
    from PySide6.QtCore import QCoreApplication  # Must precede native Dagor imports.
    _QT_APP = QCoreApplication.instance() or QCoreApplication([])
    sys.path[:0] = [str(vendor), str(vendor / "dae_core")]
    original_popen = subprocess.Popen
    if os.name == "nt":
        _DLL_HANDLES.append(os.add_dll_directory(str(vendor / "lib")))
        os.environ["PATH"] = str(vendor / "lib") + os.pathsep + os.environ.get("PATH", "")
        class HiddenPopen(original_popen):
            def __init__(self, *args, **kwargs):
                kwargs["creationflags"] = kwargs.get("creationflags", 0) | subprocess.CREATE_NO_WINDOW
                super().__init__(*args, **kwargs)
        subprocess.Popen = HiddenPopen
    try:
        from wtx.vehicles import VehicleCatalog
        catalog = VehicleCatalog(game, wt_ext, cache_root)
        catalog._prepare_icons = lambda _status: None
        status = lambda message: print(message, file=sys.stderr, flush=True)
        catalog.extract(status, use_cache=True)
        if refresh:
            native_index = project_child(project, catalog.work_dir / "catalog_cache.pkl")
            native_index.unlink(missing_ok=True)
        rows = [{"id": v.id, "name": v.name, "nation": v.nation,
                 "type": v.type, "model_id": v.model_id,
                 **({"premium": v.premium} if isinstance(getattr(v, "premium", None), bool) else {})}
                for v in catalog.scan(status)]
    finally:
        subprocess.Popen = original_popen
    vehicles = normalize_catalog(rows)
    compact_root.mkdir(parents=True, exist_ok=True)
    temporary = project_child(project, compact_root / "vehicles.tmp.json")
    temporary.write_text(json.dumps({"schema_version": SCHEMA_VERSION,
                                    "source_signature": signature, "vehicles": vehicles},
                                   ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(compact_path)
    return vehicles, {"kind": "vehicle_catalog_api", "path": str(compact_path), "source_signature": signature}


class JsonParser(argparse.ArgumentParser):
    def error(self, message):
        print(json.dumps({"status": "invalid_arguments", "exact_id": None, "error": message}))
        raise SystemExit(2)


def main(argv=None):
    parser = JsonParser(description=__doc__)
    parser.add_argument("--project", required=True, type=Path)
    parser.add_argument("--query", required=True)
    parser.add_argument("--game-dir", type=Path, default=DEFAULT_GAME)
    parser.add_argument("--catalog-json", type=Path)
    parser.add_argument("--refresh", action="store_true",
                        help="Rebuild the compact/native vehicle index; reuse signature-valid unpacked game data")
    args = parser.parse_args(argv)
    try:
        query = validate_query(args.query)  # Reject before any filesystem/cache work.
    except ValueError as error:
        print(json.dumps({"status": "invalid_query", "query": args.query,
                          "exact_id": None, "error": str(error)}))
        return 2
    try:
        with contextlib.redirect_stdout(sys.stderr):
            if args.catalog_json:
                vehicles = normalize_catalog(json.loads(args.catalog_json.read_text(encoding="utf-8-sig")))
                source = {"kind": "catalog_json", "path": str(args.catalog_json.resolve())}
            else:
                vehicles, source = load_local_catalog(args.project, args.game_dir, args.refresh)
        result = resolve(query, vehicles)
        result["catalog"] = {**source, "vehicle_count": len(vehicles)}
        # Windows shells may use a legacy encoding; JSON escapes preserve every
        # localized vehicle name without turning a successful lookup into an error.
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0  # Valid lookups may be ambiguous/no_match; callers inspect status.
    except Exception as error:
        print(json.dumps({"status": "error", "exact_id": None, "error": str(error)}, ensure_ascii=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
