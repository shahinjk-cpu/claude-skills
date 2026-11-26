"""
Dynamic Subtitles & Speed Acceleration Builder for Pipeline Outputs
Tự động tăng tốc độ video lên 1.1x (giữ nguyên cao độ âm thanh)
và ép phụ đề Karaoke động (CapCut / TikTok Style):
- Chữ mặc định màu TRẮNG (&H00FFFFFF&), viền đen siêu dày (Outline 8px, Shadow 3px)
- Đúng từ đang nói sẽ SÁNG RỰC MÀU VÀNG (&H0000E6FF&) nhảy nhịp nhàng theo câu thoại
- In hoa toàn bộ (ALL CAPS), font Roboto Black Việt Hóa kích cỡ đồng đều 100%
- Vị trí hạ thấp xuống 1/4 khung hình (MarginV = 280), thoáng mắt, an toàn phía trên footer disclaimer
"""
import subprocess
from pathlib import Path
from typing import List, Tuple

FONTS_DIR = Path(__file__).resolve().parent.parent / "fonts"

def format_ass_time(sec: float) -> str:
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = sec % 60
    return f"{h}:{m:02d}:{s:05.2f}"

def generate_karaoke_ass_file(phrases: List[Tuple[float, float, List[str], List[str]]], output_ass_path: Path, lead_in: float = 0.35):
    """
    Tạo file .ass Karaoke với từ active màu vàng, từ còn lại màu trắng,
    nhích sớm `lead_in` giây để bắt trúng từng âm tiết.
    phrases format: list of (start_t, end_t, line1_words, line2_words)
    """
    ass_events = []
    for p_start, p_end, l1_words, l2_words in phrases:
        s_adj = max(0.0, p_start - lead_in)
        e_adj = max(s_adj + 0.5, p_end - lead_in)
        all_w = l1_words + l2_words
        step = (e_adj - s_adj) / max(1, len(all_w))
        
        for idx, active_w in enumerate(all_w):
            t1 = s_adj + idx * step
            t2 = t1 + step
            
            l1_p = [f"{{\\c&H0000E6FF&}}{w}{{\\c&H00FFFFFF&}}" if w == active_w else w for w in l1_words]
            l2_p = [f"{{\\c&H0000E6FF&}}{w}{{\\c&H00FFFFFF&}}" if w == active_w else w for w in l2_words]
            txt = " ".join(l1_p) + "\\N" + " ".join(l2_p)
            
            ass_events.append(f"Dialogue: 0,{format_ass_time(t1)},{format_ass_time(t2)},Default,,0,0,0,,{txt}")

    ass_header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Roboto Black,80,&H00FFFFFF,&H0000E6FF,&H00000000,&H80000000,1,0,0,0,100,100,1,0,1,8,3,2,40,40,280,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""" + "\n".join(ass_events)

    output_ass_path.parent.mkdir(parents=True, exist_ok=True)
    output_ass_path.write_text(ass_header, encoding="utf-8")
    return output_ass_path

def apply_subtitles_and_speed(input_video: Path, output_video: Path, ass_path: Path = None, speed: float = 1.1):
    """
    Tăng tốc video lên `speed` và burn phụ đề Roboto vào video bằng ffmpeg
    """
    temp_speed = input_video.parent / f"_temp_speed_{input_video.name}"
    
    # 1. Tăng tốc 1.1x
    if speed != 1.0:
        cmd_speed = [
            "ffmpeg", "-y", "-i", str(input_video),
            "-filter_complex", f"[0:v]setpts=PTS/{speed}[v];[0:a]atempo={speed}[a]",
            "-map", "[v]", "-map", "[a]",
            "-c:v", "libx264", "-crf", "18", "-preset", "fast",
            "-c:a", "aac", "-b:a", "192k",
            str(temp_speed)
        ]
        subprocess.run(cmd_speed, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        target_in = temp_speed
    else:
        target_in = input_video

    # 2. Burn ASS Subtitles với fontsdir trỏ tới Roboto Việt hóa
    if ass_path and ass_path.exists():
        esc_ass = str(ass_path.resolve()).replace("\\", "/").replace(":", "\\:")
        esc_fonts = str(FONTS_DIR.resolve()).replace("\\", "/").replace(":", "\\:")
        cmd_sub = [
            "ffmpeg", "-y", "-i", str(target_in),
            "-vf", f"subtitles='{esc_ass}':fontsdir='{esc_fonts}'",
            "-c:v", "libx264", "-crf", "18", "-preset", "fast",
            "-c:a", "copy",
            str(output_video)
        ]
        subprocess.run(cmd_sub, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        import shutil
        shutil.copy2(target_in, output_video)

    temp_speed.unlink(missing_ok=True)
    return output_video
