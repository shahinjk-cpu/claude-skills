"""
Dialogue Auditor & Quality Controller for AI Video Pipelines
BỘ NÃO KIỂM ĐỊNH THOẠI TOÀN DIỆN (ĐỐI CHIẾU 2 CHIỀU: KỊCH BẢN VS THỰC TẾ STT)
Phát hiện triệt để:
1. Nuốt chữ / thiếu câu (Omission / Truncation)
2. Lặp từ / vấp từ (Stuttering / Repetition)
3. Cắt cụt đuôi câu (Tail Cutoff)
4. LẢM NHẢM ĐUÔI / TỰ NÓI NHẢM KHI DƯ GIÂY (Tail Babble / Hallucination Detection)
5. Thừa thoại / lệch kịch bản (Precision & Recall Violation)
"""
import os
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Tuple

try:
    import speech_recognition as sr
    STT_AVAILABLE = True
except ImportError:
    STT_AVAILABLE = False


def transcribe_video_audio(video_path: Path) -> str:
    """Trích xuất âm thanh và bóc băng tiếng Việt bằng Google STT."""
    if not STT_AVAILABLE or not video_path.exists():
        return ""
    wav_tmp = video_path.parent / f"_audit_{video_path.stem}.wav"
    cmd = [
        "ffmpeg", "-y", "-i", str(video_path),
        "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
        str(wav_tmp)
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    text = ""
    try:
        r = sr.Recognizer()
        with sr.AudioFile(str(wav_tmp)) as source:
            audio = r.record(source)
        text = r.recognize_google(audio, language="vi-VN")
    except Exception:
        text = ""
    finally:
        if wav_tmp.exists():
            try:
                wav_tmp.unlink()
            except Exception:
                pass
    return text.strip()


def extract_expected_dialogue(scene: Dict[str, Any]) -> str:
    """Trích xuất câu thoại dự kiến từ video_prompt hoặc image_prompt, loại bỏ Voice Directing & Character tags."""
    v_prompt = scene.get("video_prompt") or ""
    diag_match = re.search(r'Dialogue:\s*(.*?)(?=\s*Voice Directing|\s*Chỉ đạo giọng|$)', v_prompt, re.IGNORECASE | re.DOTALL)
    if diag_match:
        raw = diag_match.group(1).strip()
        # Loại bỏ các tag [Nhân vật]: hoặc Tên:
        cleaned = re.sub(r'\[[^\]]+\]\s*:\s*', ' ', raw)
        cleaned = re.sub(r'^[A-Za-zÀ-ỹ0-9_\s]+:\s*', ' ', cleaned)
        cleaned = cleaned.strip(' "\'“”«»')
        return " ".join(cleaned.split())
    return ""


def clean_words(text: str) -> List[str]:
    """Tách từ chuẩn hóa chữ thường loại bỏ dấu câu."""
    cleaned = re.sub(r'[^\w\s]', ' ', text.lower())
    return [w for w in cleaned.split() if w]


def compare_dialogue(expected: str, actual: str) -> Dict[str, Any]:
    """
    Thuật toán kiểm định đối chiếu 2 chiều (Bidirectional Dialogue Verification).
    Đánh giá cả:
    - RECALL (Độ phủ: Có nói đủ từ trong kịch bản không, chống nuốt chữ)
    - PRECISION (Độ chuẩn xác: Có nói thêm từ lạ ngoài kịch bản không, chống lảm nhảm đuôi)
    - TAIL ALIGNMENT (Kiểm tra phần đuôi câu để phát hiện cắt cụt hoặc babble)
    """
    issues = []
    suggested_fix = None
    
    # 1. Trường hợp không có thoại dự kiến (B-roll / cảnh hành động)
    if not expected:
        if not actual:
            return {
                "verdict": "PASSED",
                "match_rate": 1.0,
                "precision": 1.0,
                "issues": [],
                "suggested_fix": None,
                "summary": "Cảnh không thoại (B-roll/Hành động) - Hợp lệ 100%"
            }
        else:
            issues.append(f"Cảnh không thoại nhưng AI lại tự nói: '{actual[:60]}...'")
            return {
                "verdict": "FLAGGED",
                "match_rate": 0.0,
                "precision": 0.0,
                "issues": issues,
                "suggested_fix": "Chuyển prompt sang mô tả hành động thuần túy không có tag Dialogue.",
                "summary": "AI tự nói ngoài kịch bản"
            }

    # 2. Trường hợp có thoại dự kiến nhưng thực tế rỗng (Mất tiếng / lỗi âm thanh)
    if expected and not actual:
        issues.append("Âm thanh rỗng hoặc STT không nhận diện được tiếng nói (AI bị câm hoặc nuốt 100% thoại).")
        return {
            "verdict": "FAILED",
            "match_rate": 0.0,
            "precision": 0.0,
            "issues": issues,
            "suggested_fix": "Render lại video với prompt rõ ràng có tag Voice Directing và Dialogue.",
            "summary": "Mất hoàn toàn tiếng / Lỗi thoại"
        }

    exp_words = clean_words(expected)
    act_words = clean_words(actual)
    
    # Bộ từ khóa quan trọng (từ dài > 2 ký tự)
    exp_key_words = [w for w in exp_words if len(w) > 2]
    act_key_words = [w for w in act_words if len(w) > 2]

    # Kiểm tra vấp tiếng / lặp từ liên tiếp (Stutter)
    stutter_words = []
    for i in range(len(act_words) - 1):
        if act_words[i] == act_words[i+1] and len(act_words[i]) > 2:
            stutter_words.append(act_words[i])
    if stutter_words:
        issues.append(f"Phát hiện lặp từ/vấp tiếng: {', '.join(set(stutter_words))}")

    # Tính RECALL (Độ phủ kịch bản)
    matched_exp = [w for w in exp_key_words if w in act_words]
    recall = len(matched_exp) / max(1, len(exp_key_words))

    # Tính PRECISION (Độ chuẩn xác, không nói từ thừa)
    matched_act = [w for w in act_key_words if w in exp_words]
    precision = len(matched_act) / max(1, len(act_key_words))

    # KIỂM SOÁT ĐUÔI CÂU 1: CẮT CỤT ĐUÔI (Tail Cutoff / Truncation)
    tail_expected = exp_key_words[-4:] if len(exp_key_words) >= 4 else exp_key_words
    tail_matched = [w for w in tail_expected if w in act_words]
    tail_cutoff = (len(tail_matched) == 0 and len(tail_expected) > 0)
    if tail_cutoff:
        issues.append(f"CẮT CỤT ĐUÔI THOẠI: Thiếu các từ kết thúc kịch bản: '{' '.join(tail_expected)}'")
        if not suggested_fix:
            suggested_fix = "Tăng thời lượng video (+2s) hoặc tăng tốc độ đọc của nhân vật."

    # KIỂM SOÁT ĐUÔI CÂU 2: LẢM NHẢM ĐUÔI (Tail Babble / Hallucination) - LỖI NGUY HIỂM NHẤT!
    # Tìm vị trí từ khóa cuối cùng của kịch bản xuất hiện trong thực tế
    last_matched_idx = -1
    for i, w in enumerate(act_words):
        if w in exp_key_words:
            last_matched_idx = i

    tail_babble_words = []
    if last_matched_idx != -1 and (len(act_words) - 1 - last_matched_idx) >= 4:
        # Có từ 4 từ trở lên nói tiếp sau từ khóa cuối cùng của kịch bản
        excess_tail = act_words[last_matched_idx + 1:]
        # Kiểm tra xem những từ thừa này có thuộc kịch bản không
        unwanted_tail = [w for w in excess_tail if w not in exp_words]
        if len(unwanted_tail) >= 3:
            tail_babble_words = excess_tail
            issues.append(f"LẢM NHẢM ĐUÔI (TAIL BABBLE): AI nói thêm {len(excess_tail)} từ lạ sau khi kết thúc kịch bản: '{' '.join(excess_tail)}'")
            if not suggested_fix:
                suggested_fix = "Giảm thời lượng video_length (-2s đến -3s) để triệt tiêu thời gian chết gây lặp từ/nói nhảm."

    # Kiểm tra độ dài bất thường (Length Ratio)
    len_ratio = len(act_words) / max(1, len(exp_words))
    if len_ratio > 1.35 and not tail_babble_words:
        issues.append(f"Thoại thực tế dài hơn kịch bản {int((len_ratio - 1)*100)}% (Có thể có từ lặp hoặc câu thừa).")
        if not suggested_fix:
            suggested_fix = "Kiểm tra lại Voice Directing và cắt giảm video_length."
    elif len_ratio < 0.60:
        issues.append(f"Thoại thực tế quá ngắn so với kịch bản (chỉ đạt {int(len_ratio*100)}% độ dài, nghi vấn nuốt chữ nặng).")
        if not suggested_fix:
            suggested_fix = "Tăng thời lượng video_length (+2s đến +4s)."

    # Đánh giá độ phủ kịch bản chung
    if recall < 0.65:
        issues.append(f"Độ phủ kịch bản thấp ({recall*100:.0f}%), thiếu nhiều ý chính trong câu thoại.")
        if not suggested_fix:
            suggested_fix = "Render lại cảnh với prompt thoại rõ ràng."

    # XÁC ĐỊNH VERDICT CUỐI CÙNG
    is_failed = False
    if recall < 0.60:
        is_failed = True
    if tail_cutoff:
        is_failed = True
    if len(tail_babble_words) >= 4:
        is_failed = True
    if len(stutter_words) >= 3:
        is_failed = True

    verdict = "FAILED" if is_failed else ("FLAGGED" if issues else "PASSED")

    return {
        "verdict": verdict,
        "is_passed": (verdict == "PASSED"),
        "match_rate": recall,
        "precision": precision,
        "issues": issues,
        "suggested_fix": suggested_fix,
        "tail_babble": " ".join(tail_babble_words) if tail_babble_words else None,
        "expected_word_count": len(exp_words),
        "actual_word_count": len(act_words)
    }


def audit_single_scene(scene: Dict[str, Any], storage_dir: Path) -> Dict[str, Any]:
    """Kiểm tra bóc băng STT tức thì cho 1 cảnh ngay khi vừa render xong (Real-time)."""
    sid = scene.get("id")
    raw_vid = storage_dir / f"scene_{sid}_video.mp4"
    trim_vid = storage_dir / "_snappy_trimmed" / f"trimmed_sc_{sid}.mp4"
    target_vid = trim_vid if trim_vid.exists() else raw_vid

    expected = extract_expected_dialogue(scene)
    actual = transcribe_video_audio(target_vid) if target_vid.exists() else ""

    res = compare_dialogue(expected, actual)
    res["id"] = sid
    res["expected"] = expected
    res["actual"] = actual
    return res


def audit_scenes_dialogue(scenes: List[Dict[str, Any]], storage_dir: Path) -> Dict[str, Any]:
    """
    Thực hiện bóc băng và đối chiếu toàn bộ thoại các cảnh.
    CHẶN ĐỨNG GHÉP NỐI NẾU CÓ BẤT KỲ CẢNH NÀO FAILED!
    """
    print("\n" + "="*80)
    print("🔍 [BỘ NÃO AUDITOR] KIỂM ĐỊNH THOẠI 2 CHIỀU TOÀN DIỆN (KỊCH BẢN VS THỰC TẾ STT)")
    print("="*80)

    results = {}
    failed_scenes = []
    flagged_scenes = []

    for sc in scenes:
        sid = sc.get("id")
        audit_res = audit_single_scene(sc, storage_dir)
        results[sid] = audit_res

        v_symbol = "✅ PASSED" if audit_res["verdict"] == "PASSED" else ("⚠️ FLAGGED" if audit_res["verdict"] == "FLAGGED" else "❌ FAILED")
        print(f"\n[CẢNH {sid}] - Kết quả: {v_symbol} (Phủ: {audit_res['match_rate']*100:.0f}% | Chuẩn: {audit_res['precision']*100:.0f}%)")
        if audit_res.get("expected"):
            print(f"  • Kịch bản ({audit_res['expected_word_count']} từ): \"{audit_res['expected']}\"")
        print(f"  • Thực tế ({audit_res['actual_word_count']} từ): \"{audit_res['actual']}\"")

        if audit_res["issues"]:
            for iss in audit_res["issues"]:
                print(f"  ❌ Lỗi: {iss}")
            if audit_res.get("suggested_fix"):
                print(f"  💡 Giải pháp đề xuất: {audit_res['suggested_fix']}")

        if audit_res["verdict"] == "FAILED":
            failed_scenes.append(sid)
        elif audit_res["verdict"] == "FLAGGED":
            flagged_scenes.append(sid)

    print("\n" + "="*80)
    all_passed = (len(failed_scenes) == 0)
    if not all_passed:
        print(f"❌ [CẢNH BÁO NGHIÊM NGẶT] CÓ {len(failed_scenes)} CẢNH THẤT BẠI KIỂM ĐỊNH THOẠI: {failed_scenes}")
        print("⛔ LỆNH CHẶN: TUYỆT ĐỐI KHÔNG ĐƯỢC PHÉP GHÉP NỐI VIDEO KHI CÒN CẢNH LỖI THOẠI/LẢM NHẢM!")
    elif flagged_scenes:
        print(f"⚠️ [LƯU Ý] Tất cả các cảnh đạt chuẩn cơ bản, có {len(flagged_scenes)} cảnh cần lưu ý nhẹ: {flagged_scenes}")
    else:
        print("✅ [HOÀN HẢO] 100% CÁC PHÂN CẢNH ĐẠT CHUẨN THOẠI TUYỆT ĐỐI! SẴN SÀNG GHÉP NỐI!")
    print("="*80 + "\n")

    return {
        "all_passed": all_passed,
        "failed_scenes": failed_scenes,
        "flagged_scenes": flagged_scenes,
        "details": results
    }
