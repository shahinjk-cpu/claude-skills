import os
import sys
import subprocess
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from kich_ban_to_video.scripts.snappy_trimmer import trim_scene_snappy, get_video_duration, detect_exact_speech_end
from kich_ban_to_video.scripts.add_footer import apply_footer_to_video
from kich_ban_to_video.scripts.gdrive_uploader import upload_video_to_gdrive
from kich_ban_to_video.scripts.dialogue_auditor import transcribe_video_audio

def main():
    print("=== TIẾN HÀNH HẬU KỲ VÀ GHÉP TỰ ĐỘNG SERIES HỒ BƠI RESORT VÔ CỰC ===")
    
    storage_dir = Path("web_glabs_studio/storage/task_20261113_233034")
    proj_dir = Path("kich_ban_to_video/projects/cottonday_resort_infinity_pool")
    out_dir = proj_dir / "outputs"
    trimmed_dir = out_dir / "trimmed_scenes"
    trimmed_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Đo đạc & Cắt tỉa Snappy Trim cho từng cảnh
    print("\n[*] 1. Đang tiến hành Snappy Trim độc lập từng cảnh...")
    stats = []
    trimmed_files = []
    total_saved = 0.0
    
    for sid in range(1, 10):
        src = storage_dir / f"scene_{sid}_video.mp4"
        dst = trimmed_dir / f"trimmed_scene_{sid}.mp4"
        orig_dur = get_video_duration(src)
        speech_end = detect_exact_speech_end(src)
        saved = trim_scene_snappy(src, dst, buffer_sec=0.15)
        new_dur = get_video_duration(dst)
        stt = transcribe_video_audio(dst)
        total_saved += saved
        trimmed_files.append(dst)
        stats.append({
            "scene": sid,
            "orig_dur": orig_dur,
            "speech_end": speech_end,
            "saved": saved,
            "trimmed_dur": new_dur,
            "stt": stt
        })
        print(f"    Cảnh {sid}: Gốc {orig_dur:.2f}s | Dứt thoại {speech_end:.2f}s | Gọt {saved:.2f}s -> Còn {new_dur:.2f}s")
        print(f"    STT: {stt}")

    print(f"\n[✓] Hoàn thành Snappy Trim 9 cảnh! Tổng thời gian thừa đã gọt: {total_saved:.2f}s")
    
    # 2. Ghép nối duy nhất 1 lần (Concat)
    concat_list = out_dir / "concat_list.txt"
    with open(concat_list, "w", encoding="utf-8") as f:
        for clip in trimmed_files:
            norm_path = str(clip.resolve()).replace("\\", "/")
            f.write(f"file '{norm_path}'\n")
            
    raw_merged = out_dir / "raw_merged.mp4"
    print("\n[*] 2. Đang ghép nối 9 phân cảnh đã cắt tỉa...")
    cmd_merge = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(concat_list),
        "-c", "copy",
        str(raw_merged)
    ]
    subprocess.run(cmd_merge, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    raw_dur = get_video_duration(raw_merged)
    print(f"[✓] Ghép thành công raw video: {raw_dur:.2f}s")
    
    # 3. Tăng tốc 1.1x (Pitch Preserved)
    speed_merged = out_dir / "speed_1_1x_merged.mp4"
    print("\n[*] 3. Đang tăng tốc 1.1x bảo toàn cao độ âm thanh...")
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
    print(f"[✓] Hoàn tất tăng tốc 1.1x: {speed_dur:.2f}s")
    
    # 4. Đóng dấu Footer miễn trừ trách nhiệm
    target_name = "Series Cottonday - Ho Boi Resort Vo Cuc (Donghua 3D Unreal Engine 5).mp4"
    final_video = out_dir / target_name
    print("\n[*] 4. Đang đóng dấu Footer miễn trừ trách nhiệm sản phẩm...")
    apply_footer_to_video(speed_merged, final_video)
    final_dur = get_video_duration(final_video)
    print(f"[✓] Hoàn tất video có footer: {final_video.name} ({final_dur:.2f}s)")
    
    # 5. Trích xuất frame xác nhận footer
    verify_frame = Path("C:/Users/Administrator/.gemini/antigravity/brain/6af77bea-f1b7-4500-95cb-1f0ce7611774/resort_final_verified_footer.jpg")
    cmd_frame = [
        "ffmpeg", "-y", "-ss", "00:00:08", "-i", str(final_video),
        "-frames:v", "1", "-q:v", "2", str(verify_frame)
    ]
    subprocess.run(cmd_frame, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"[✓] Đã trích xuất frame xác nhận footer: {verify_frame}")
    
    # 6. Upload Google Drive
    print(f"\n[*] 5. Đang tải lên Google Drive thư mục 1LQfVRoejxpoQLjgR_piVd1TuNUEH_Hra...")
    res = upload_video_to_gdrive(final_video, custom_filename=target_name)
    print(f"[✓] TẢI LÊN GOOGLE DRIVE THÀNH CÔNG!")
    print(f"    - ID: {res.get('file_id')}")
    print(f"    - View Link: {res.get('web_view_link')}")
    print(f"    - Download Link: {res.get('direct_download_link')}")
    
    # 7. Dọn dẹp file tạm theo Rule 16
    print("\n[*] 6. Dọn dẹp file tạm và giải phóng dung lượng ổ đĩa...")
    for f in [raw_merged, speed_merged, concat_list, final_video]:
        try:
            f.unlink()
        except Exception:
            pass
            
    # Lưu báo cáo stats
    stats_file = out_dir / "render_stats.json"
    import json
    stats_file.write_text(json.dumps({
        "stats": stats,
        "total_saved": total_saved,
        "final_duration": final_dur,
        "gdrive": res
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    
    print("\n=== HOÀN TẤT TOÀN DIỆN QUY TRÌNH ===")

if __name__ == "__main__":
    main()
