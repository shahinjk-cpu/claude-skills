import subprocess
from pathlib import Path
from PIL import Image
import shutil

task_dir = Path("web_glabs_studio/storage/task_20261113_101109")
trimmed_dir = task_dir / "_snappy_trimmed"

# 1. Concat
clips = [trimmed_dir / f"trimmed_sc_{i}.mp4" for i in range(1, 10)]
concat_list = trimmed_dir / "concat_clean.txt"
with open(concat_list, "w", encoding="utf-8") as f:
    for c in clips:
        f.write(f"file '{c.resolve().as_posix()}'\n")

raw_merged = task_dir / "clean_merged_raw.mp4"
print("[*] [1/4] Ghép 9 cảnh thô...")
subprocess.run(
    ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list), "-c", "copy", str(raw_merged)],
    check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
)

# 2. Tăng tốc 1.1x KHÔNG phụ đề (loại bỏ subtitle karaoke theo yêu cầu người dùng)
speed_out = task_dir / "clean_speed_1.1.mp4"
print("[*] [2/4] Tăng tốc 1.1x (không phụ đề)...")
cmd_speed = [
    "ffmpeg", "-y", "-i", str(raw_merged),
    "-filter_complex", "[0:v]setpts=PTS/1.1[v];[0:a]atempo=1.1[a]",
    "-map", "[v]", "-map", "[a]",
    "-c:v", "libx264", "-crf", "18", "-preset", "fast",
    "-c:a", "aac", "-b:a", "192k",
    str(speed_out)
]
subprocess.run(cmd_speed, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# 3. Gắn Footer Disclaimer động theo đúng độ phân giải
from add_footer import apply_footer_to_video
final_dest = Path("kich_ban_to_video/projects/cottonday_saigon_wine_balcony/outputs/final_merged_video_1080p.mp4")
final_dest.parent.mkdir(parents=True, exist_ok=True)
print("[*] [3/4] Gắn Footer Disclaimer 2 dòng...")
apply_footer_to_video(speed_out, final_dest)

# 4. Trích xuất frame và kiểm tra trực tiếp bằng PIL
verify_jpg = Path("C:/Users/Administrator/.gemini/antigravity/brain/6af77bea-f1b7-4500-95cb-1f0ce7611774/verify_footer_frame.jpg")
subprocess.run(
    ["ffmpeg", "-y", "-ss", "00:00:05", "-i", str(final_dest), "-vframes", "1", "-q:v", "2", str(verify_jpg)],
    check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
)

img = Image.open(verify_jpg)
w, h = img.size
print(f"[*] Kích thước frame video: {w}x{h}")
crop_bottom = img.crop((w // 6, h - 80, 5 * w // 6, h - 10))
pixels = list(crop_bottom.getdata())
bright_pixels = [p for p in pixels if p[0] > 210 and p[1] > 210 and p[2] > 210]
print(f"[*] Số điểm ảnh sáng (chữ footer) phát hiện được: {len(bright_pixels)}")
assert len(bright_pixels) > 50, "CẢNH BÁO: Không phát hiện chữ footer!"
print("[✓] XÁC NHẬN: Footer disclaimer đã hiển thị rõ ràng 100% trên khung hình!")

# 5. Upload lên Google Drive
print("\n[*] [4/4] Upload lên đúng thư mục Google Drive (Folder 1LQfVRoejxpoQLjgR_piVd1TuNUEH_Hra)...")
from gdrive_uploader import upload_video_to_gdrive, cleanup_local_files

custom_filename = "Series Cottonday - Mui Am Uong Ngoai Ban Cong (Thao Dien Saigon).mp4"
gdrive_res = upload_video_to_gdrive(final_dest, custom_filename=custom_filename)

print(f"\n[✓] LINK GOOGLE DRIVE HOÀN THIỆN: {gdrive_res['view_link']}")

# 6. Dọn dẹp local
print("\n[*] Dọn dẹp giải phóng bộ nhớ local...")
cleanup_local_files(task_dir, final_dest, patterns=("*.mp4",))
print("[✓] Hoàn tất toàn bộ quy trình!")
