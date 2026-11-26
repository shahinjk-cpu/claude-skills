import os
import sys
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from kich_ban_to_video.scripts.snappy_trimmer import trim_scene_snappy, get_video_duration
from kich_ban_to_video.scripts.add_footer import apply_footer_to_video
from kich_ban_to_video.scripts.gdrive_uploader import upload_video_to_gdrive

def main():
    print("=== BẮT ĐẦU QUY TRÌNH GHÉP VÀ BÀN GIAO VIDEO HOÀN THIỆN V2 ===")
    
    # 1. Định nghĩa 9 nguồn video chuẩn 100%
    p1 = Path("web_glabs_studio/storage/task_20261113_202915")
    p2 = Path("web_glabs_studio/storage/task_20261113_223000")
    
    scene_sources = {
        1: p1 / "scene_1_video.mp4",
        2: p1 / "scene_2_video.mp4",
        3: p1 / "scene_3_video.mp4",
        4: p1 / "scene_4_video.mp4",
        5: p2 / "scene_5_video.mp4",  # Bản đầy đủ hết câu "vô ví đi tiệc nghe em!"
        6: p1 / "scene_6_video.mp4",  # Bản 14s khẩu hình Lan Anh chuẩn "hổng hề vón cục"
        7: p1 / "scene_7_video.mp4",  # Bản 37 độ xông ấm
        8: p1 / "scene_8_video.mp4",  # Bản đối thoại Đức & Mai lột xác
        9: p1 / "scene_9_video.mp4",  # Bản 13s CTA dứt khoát "chốt liền nghen"
    }
    
    for sid, src in scene_sources.items():
        if not src.exists():
            raise FileNotFoundError(f"Không tìm thấy video Cảnh {sid} tại: {src}")
        print(f"[✓] Cảnh {sid}: {src.name} ({get_video_duration(src):.2f}s)")
        
    # 2. Snappy Trim từng cảnh
    work_dir = Path("kich_ban_to_video/projects/cottonday_donghua_gala_ballroom_v2/outputs")
    work_dir.mkdir(parents=True, exist_ok=True)
    staging_dir = work_dir / "_staging_snappy"
    staging_dir.mkdir(parents=True, exist_ok=True)
    
    trimmed_clips = []
    total_saved = 0.0
    for sid in range(1, 10):
        src = scene_sources[sid]
        dst = staging_dir / f"trimmed_scene_{sid}.mp4"
        print(f"[*] Đang Snappy Trim Cảnh {sid}...")
        saved = trim_scene_snappy(src, dst, buffer_sec=0.15)
        total_saved += saved
        dur = get_video_duration(dst)
        print(f"    -> Đã gọt {saved:.2f}s | Thời lượng còn lại: {dur:.2f}s")
        trimmed_clips.append(dst)
        
    print(f"\n[✓] Hoàn thành Snappy Trim 9 cảnh. Tổng thời gian gọt bỏ: {total_saved:.2f}s")
    
    # 3. Ghép nối danh sách video
    concat_list = staging_dir / "concat_list.txt"
    with open(concat_list, "w", encoding="utf-8") as f:
        for clip in trimmed_clips:
            norm_path = str(clip.resolve()).replace("\\", "/")
            f.write(f"file '{norm_path}'\n")
            
    raw_merged = staging_dir / "raw_merged.mp4"
    cmd_merge = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(concat_list),
        "-c", "copy",
        str(raw_merged)
    ]
    subprocess.run(cmd_merge, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    raw_dur = get_video_duration(raw_merged)
    print(f"[✓] Ghép thành công raw merged video: {raw_dur:.2f}s")
    
    # 4. Tăng tốc 1.1x (Pitch Preserved)
    speed_merged = staging_dir / "speed_1_1x_merged.mp4"
    print("[*] Đang tăng tốc 1.1x video (bảo toàn cao độ âm thanh giọng nói)...")
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
    final_footer_vid = staging_dir / "final_with_footer.mp4"
    print("[*] Đang đóng dấu Footer miễn trừ trách nhiệm sản phẩm...")
    apply_footer_to_video(speed_merged, final_footer_vid)
    print(f"[✓] Đã đóng dấu Footer thành công: {final_footer_vid}")
    
    # 6. Trích xuất frame xác nhận footer
    verify_frame = Path("C:/Users/Administrator/.gemini/antigravity/brain/6af77bea-f1b7-4500-95cb-1f0ce7611774/final_v2_perfect_footer.jpg")
    cmd_frame = [
        "ffmpeg", "-y", "-ss", "00:00:05", "-i", str(final_footer_vid),
        "-frames:v", "1", "-q:v", "2", str(verify_frame)
    ]
    subprocess.run(cmd_frame, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"[✓] Đã trích xuất frame kiểm định footer: {verify_frame}")
    
    # 7. Upload Google Drive
    target_name = "Series Cottonday - Kiep Nguoi Giu Gio Xach (Donghua 3D Unreal Engine 5 V2).mp4"
    print(f"[*] Đang tải lên Google Drive với tên: {target_name}...")
    res = upload_video_to_gdrive(final_footer_vid, custom_filename=target_name)
    print(f"\n[✓] UPLOAD THÀNH CÔNG LÊN GOOGLE DRIVE!")
    print(f"    - File ID: {res.get('file_id')}")
    print(f"    - Web View Link: {res.get('web_view_link')}")
    print(f"    - Direct Download: {res.get('direct_download_link')}")
    
    # Dọn dẹp staging sau khi hoàn tất
    print("[*] Dọn dẹp thư mục staging tạm...")
    for f in staging_dir.glob("*"):
        try:
            f.unlink()
        except Exception:
            pass
    try:
        staging_dir.rmdir()
    except Exception:
        pass
    print("[✓] Hoàn tất toàn bộ quy trình sạch sẽ!")

if __name__ == "__main__":
    main()
