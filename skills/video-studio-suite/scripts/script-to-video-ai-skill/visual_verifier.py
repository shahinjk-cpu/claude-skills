"""
Visual QA Frame Extractor & Speaker Lip-Sync Lock
Đảm bảo quy tắc AGENT VISION-FIRST:
- KHÔNG dùng tool hay thuật toán cơ học để đoán bừa dị tật thị giác
- Tự động trích xuất các frame tiêu biểu chất lượng cao để AI Agent (Antigravity) tự mở mắt xem và đánh giá
- Tự động tiêm câu lệnh khóa khẩu hình người nói và khóa số lượng nhân vật tuyệt đối
"""
import os
import re
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional


def auto_lock_speaker_and_characters(prompt: str) -> str:
    """
    Tự động nhận diện nhân vật thoại và tiêm khóa khẩu hình + giới hạn số nhân vật vào prompt:
    - Đảm bảo CHỈ DUY NHẤT nhân vật phát âm mở miệng nhép lời (ngẩng mặt hướng ra trước, tầm nhìn miệng rõ ràng)
    - Các nhân vật khác phải mím chặt môi im lặng, hơi cúi đầu hoặc nhìn nghiêng
    - Cấm tiệt nhân vật thứ 4 hay cánh tay lạ thò vào từ mép khung hình
    """
    speaker = None
    diag_match = re.search(r'(?:Dialogue|Thoại)\s*:\s*(?:\[([^\]]+)\]\s*:|([A-ZÀ-Ỹa-zà-ỹ\s]+)\s*:)?\s*["“\']?(.*?)["”\']?$', prompt, re.IGNORECASE | re.DOTALL)
    if diag_match:
        speaker = diag_match.group(1) or diag_match.group(2)
    
    if not speaker:
        vd_match = re.search(r'Voice Directing\s*:\s*.*?\(([^\)]+)\)', prompt, re.IGNORECASE)
        if vd_match:
            speaker = vd_match.group(1).strip()

    if not speaker:
        speaker = "nhân vật chính"

    speaker_lock_vi = (
        f"Chỉ có duy nhất {speaker} ngẩng mặt hướng về phía người xem/camera mở khẩu hình miệng nói dứt khoát rõ chữ theo lời thoại, không cúi gằm mặt hay để vật thể che khuất miệng. "
        "Các nhân vật khác trong phòng mím chặt môi im lặng lắng nghe, hơi cúi đầu hoặc nhìn nghiêng chăm chú vào sự việc, tuyệt đối không nhép miệng, không mở môi."
    )
    # Nhận diện số lượng nhân vật xuất hiện trong prompt
    is_solo = any(w in prompt.lower() for w in ["đứng một mình", "nép sau", "bước một mình", "độc thoại", "ngồi một mình", "alone", "single character", "solo"])
    
    if is_solo:
        character_lock_en = (
            f"Strictly a SINGLE CHARACTER shot. Strictly only {speaker} alone in the scene, facing camera with a clear unobstructed mouth view. "
            "Absolutely NO second person, NO child, NO elderly person, NO background crowd, NO extra foreign arms entering from borders."
        )
    else:
        character_lock_en = (
            f"Strictly only {speaker} speaks, facing camera with a clear unobstructed view of their mouth while articulating words. "
            "All other characters keep their lips firmly closed in silence with zero mouth movement, looking attentively aside. "
            "Strictly maintain ONLY the declared characters in the scene. Absolutely NO extra people, NO clone twins, NO extra foreign arms entering from borders."
        )

    if speaker_lock_vi not in prompt and "Strictly only" not in prompt:
        return f"{speaker_lock_vi} {character_lock_en} {prompt}"
    return prompt


def extract_scene_inspection_frames(video_path: Path, output_dir: Optional[Path] = None, timestamps: Optional[List[float]] = None) -> List[Path]:
    """
    Trích xuất các khung hình tiêu biểu (Key Sample Frames) để Trợ Lý AI tự mở mắt xem và thẩm định trực tiếp.
    """
    if output_dir is None:
        output_dir = video_path.parent / "_inspection_frames"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if not timestamps:
        timestamps = [3.0, 6.0, 9.0]

    extracted = []
    for ts in timestamps:
        out_frame = output_dir / f"{video_path.stem}_frame_{int(ts)}s.png"
        cmd = [
            "ffmpeg", "-ss", str(ts),
            "-i", str(video_path),
            "-vframes", "1",
            "-y", str(out_frame)
        ]
        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            if out_frame.exists() and out_frame.stat().st_size > 1000:
                extracted.append(out_frame)
        except Exception:
            pass
    return extracted


def prepare_scene_inspection(video_path: Path) -> Dict[str, Any]:
    """
    Chuẩn bị dữ liệu khung hình để AI Agent tự thẩm định (Vision-First Protocol).
    """
    frames = extract_scene_inspection_frames(video_path)
    return {
        "status": "ready_for_agent_review",
        "frames": [str(f.resolve()) for f in frames],
        "message": "Các khung hình đã được trích xuất sẵn sàng cho AI Agent tự mở mắt xem và kết luận."
    }

