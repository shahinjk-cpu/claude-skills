"""
Footer Disclaimer Overlay Utility
Tạo lớp phủ chữ nhỏ căn giữa dưới cùng video (tầm 50% chiều ngang khung hình) xuyên suốt video.
"""
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter


def get_video_dimensions(video_path: Path) -> tuple:
    """Lấy độ phân giải thực tế (width, height) của video bằng ffprobe."""
    cmd = [
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "csv=s=x:p=0", str(video_path)
    ]
    out = subprocess.check_output(cmd).decode().strip()
    w, h = out.split("x")
    return int(w), int(h)


def create_footer_overlay(
    output_png: Path,
    width: int = 1080,
    height: int = 1920,
    line1: str = "Sản phẩm không phải là thuốc, không thay thế thuốc chữa bệnh.",
    line2: str = "Hiệu quả nhanh hay chậm tùy cơ địa từng người.",
    font_size: int = None
) -> Path:
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Tự động co giãn cỡ chữ và lề theo đúng độ phân giải thực tế của video
    scale_w = width / 1080.0
    scale_h = height / 1920.0
    
    if font_size is None:
        font_size = max(13, int(22 * scale_w))
    line_gap = max(4, int(6 * scale_h))
    bottom_margin = max(18, int(28 * scale_h))

    font_path = "C:/Windows/Fonts/segoeui.ttf"
    if not Path(font_path).exists():
        font_path = "C:/Windows/Fonts/arial.ttf"
    font = ImageFont.truetype(font_path, font_size)

    # Tính kích thước từng dòng
    bbox1 = draw.textbbox((0, 0), line1, font=font)
    w1, h1 = bbox1[2] - bbox1[0], bbox1[3] - bbox1[1]

    bbox2 = draw.textbbox((0, 0), line2, font=font)
    w2, h2 = bbox2[2] - bbox2[0], bbox2[3] - bbox2[1]

    y2 = height - bottom_margin - h2
    y1 = y2 - line_gap - h1

    x1 = (width - w1) // 2
    x2 = (width - w2) // 2

    # Vẽ bóng đổ đen mờ (shadow layer) để đọc rõ trên mọi nền
    shadow_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(shadow_layer)
    for dx, dy in [(-1, -1), (1, -1), (-1, 1), (1, 1), (0, 2)]:
        sdraw.text((x1 + dx, y1 + dy), line1, font=font, fill=(0, 0, 0, 220))
        sdraw.text((x2 + dx, y2 + dy), line2, font=font, fill=(0, 0, 0, 220))
    shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(radius=1.5))

    img = Image.alpha_composite(img, shadow_layer)
    draw = ImageDraw.Draw(img)

    # Vẽ chữ trắng sắc nét
    draw.text((x1, y1), line1, font=font, fill=(248, 248, 248, 240))
    draw.text((x2, y2), line2, font=font, fill=(248, 248, 248, 240))

    img.save(output_png, "PNG")
    print(f"[✓] Created footer overlay PNG: {output_png} ({width}x{height}, y1={y1}, y2={y2}, font_size={font_size})")
    return output_png


def apply_footer_to_video(video_path: Path, output_path: Path):
    vid_w, vid_h = get_video_dimensions(video_path)
    print(f"[*] Detected video dimensions for footer overlay: {vid_w}x{vid_h}")
    
    overlay_png = video_path.parent / "_footer_overlay.png"
    create_footer_overlay(overlay_png, width=vid_w, height=vid_h)

    # Nếu input trùng output, ghi vào file tạm rồi đổi tên để tránh ffmpeg deadlock
    is_same = video_path.resolve() == output_path.resolve()
    actual_out = video_path.parent / f"_footer_tmp_{video_path.name}" if is_same else output_path

    cmd = [
        "ffmpeg", "-y", "-i", str(video_path), "-i", str(overlay_png),
        "-filter_complex", "[0:v][1:v]overlay=0:0",
        "-c:v", "libx264", "-crf", "18", "-preset", "fast",
        "-c:a", "copy",
        str(actual_out)
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        overlay_png.unlink()
    except Exception:
        pass

    if is_same:
        import shutil
        shutil.move(str(actual_out), str(output_path))

    print(f"[✓] Applied footer disclaimer cleanly to: {output_path}")


if __name__ == "__main__":
    import sys
    in_vid = Path(sys.argv[1])
    out_vid = Path(sys.argv[2])
    apply_footer_to_video(in_vid, out_vid)
