import os
import sys
import subprocess
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from kich_ban_to_video.scripts.add_footer import apply_footer_to_video
from kich_ban_to_video.scripts.gdrive_uploader import upload_video_to_gdrive
from kich_ban_to_video.scripts.snappy_trimmer import get_video_duration

def main():
    print("=== THỰC HIỆN CÔNG ĐOẠN KHÓA SỔ CUỐI CÙNG (FINAL MERGE & DELIVERY) ===")
    
    trimmed_dir = Path("kich_ban_to_video/projects/cottonday_donghua_gala_ballroom_v2/outputs/trimmed_scenes")
    outputs_dir = Path("kich_ban_to_video/projects/cottonday_donghua_gala_ballroom_v2/outputs")
    
    # 1. Kiểm tra đủ 9 file đã trim
    trimmed_files = []
    for sid in range(1, 10):
        f = trimmed_dir / f"trimmed_scene_{sid}.mp4"
        if not f.exists():
            raise FileNotFoundError(f"Không tìm thấy file: {f}")
        trimmed_files.append(f)
        print(f"[✓] Đã sẵn sàng Cảnh {sid}: {f.name} ({get_video_duration(f):.2f}s)")
        
    # 2. Tạo danh sách concat
    concat_list = outputs_dir / "concat_list.txt"
    with open(concat_list, "w", encoding="utf-8") as f:
        for clip in trimmed_files:
            norm_path = str(clip.resolve()).replace("\\", "/")
            f.write(f"file '{norm_path}'\n")
            
    # 3. Ghép video (concat)
    raw_merged = outputs_dir / "raw_merged.mp4"
    print("\n[*] Đang tiến hành ghép nối 9 phân cảnh đã cắt tỉa...")
    cmd_merge = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(concat_list),
        "-c", "copy",
        str(raw_merged)
    ]
    subprocess.run(cmd_merge, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    raw_dur = get_video_duration(raw_merged)
    print(f"[✓] Ghép thành công raw video: {raw_dur:.2f}s")
    
    # 4. Tăng tốc 1.1x (Pitch Preserved)
    speed_merged = outputs_dir / "speed_1_1x_merged.mp4"
    print("[*] Đang tăng tốc 1.1x (bảo toàn cao độ âm thanh giọng nói)...")
    cmd_speed = [
        "ffmpeg", "-y", "-i", str(raw_merged),
        "-filter_complex", "[0:v]setpts=PTS/1.1[v];[0:a]atempo=1.1[a]",
        "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-crf", "18", "-preset", "fast",
        "-c:a", "aac", "-b:a", "192k",
        str(speed_merged)
    ]
    subprocess.run(cmd_speed, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    speed_dur = get_video_duration(speed_merged)
    print(f"[✓] Hoàn tất tăng tốc 1.1x. Thời lượng mới: {speed_dur:.2f}s")
    
    # 5. Đóng dấu Footer miễn trừ trách nhiệm
    final_video = outputs_dir / "Series Cottonday - Kiep Nguoi Giu Gio Xach (Donghua 3D Unreal Engine 5 V2).mp4"
    print("[*] Đang đóng dấu Footer miễn trừ trách nhiệm sản phẩm...")
    apply_footer_to_video(speed_merged, final_video)
    final_dur = get_video_duration(final_video)
    print(f"[✓] Đã tạo thành công video hoàn thiện: {final_video.name} ({final_dur:.2f}s)")
    
    # 6. Trích xuất frame xác nhận Footer
    verify_frame = Path("C:/Users/Administrator/.gemini/antigravity/brain/6af77bea-f1b7-4500-95cb-1f0ce7611774/final_v2_verified_footer.jpg")
    cmd_frame = [
        "ffmpeg", "-y", "-ss", "00:00:08", "-i", str(final_video),
        "-frames:v", "1", "-q:v", "2", str(verify_frame)
    ]
    subprocess.run(cmd_frame, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"[✓] Đã trích xuất frame kiểm định footer: {verify_frame}")
    
    # 7. Upload Google Drive
    target_name = "Series Cottonday - Kiep Nguoi Giu Gio Xach (Donghua 3D Unreal Engine 5 V2).mp4"
    print(f"\n[*] Đang tải lên Google Drive thư mục cố định của anh...")
    res = upload_video_to_gdrive(final_video, custom_filename=target_name)
    print(f"[✓] TẢI LÊN GOOGLE DRIVE THÀNH CÔNG!")
    print(f"    - File ID: {res.get('file_id')}")
    print(f"    - View Link: {res.get('web_view_link')}")
    print(f"    - Download Link: {res.get('direct_download_link')}")
    
    # 8. Dọn dẹp các file nặng trung gian
    print("\n[*] Dọn dẹp các file tạm trung gian...")
    for tmp in [raw_merged, speed_merged, concat_list]:
        try:
            tmp.unlink()
        except Exception:
            pass
    # Xóa file video mp4 trong project outputs theo Rule 16
    try:
        final_video.unlink()
    except Exception:
        pass
    print("[✓] Đã giải phóng dung lượng ổ đĩa theo Rule 16.")
    
    # Trả về kết quả
    return res

if __name__ == "__main__":
    main()
