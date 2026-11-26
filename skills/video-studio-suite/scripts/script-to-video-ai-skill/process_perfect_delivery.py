"""
Process Perfect Delivery for Cottonday Saigon Wine Balcony
1. Concat 9 trimmed scene clips (including newly re-rendered Scene 1 with dramatic emotion)
2. Generate full dynamic Karaoke .ass subtitles with Roboto Black, yellow active words, 0.35s early lead-in, MarginV=280
3. Accelerate to 1.1x speed (pitch preserved) and burn subtitles
4. Burn 2-line Footer Disclaimer at bottom
5. Upload/Replace to Google Drive Folder 1LQfVRoejxpoQLjgR_piVd1TuNUEH_Hra
6. Verify and clean up local video files to free memory
"""
import sys
import os
import json
import subprocess
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = BASE_DIR / "projects" / "cottonday_saigon_wine_balcony"
TASK_DIR = Path("web_glabs_studio/storage/task_20261113_101109")
TRIMMED_DIR = TASK_DIR / "_snappy_trimmed"
FONTS_DIR = BASE_DIR / "fonts"

sys.path.append(str(BASE_DIR / "scripts"))
from subtitles_builder import format_ass_time, generate_karaoke_ass_file
from add_footer import create_footer_overlay, apply_footer_to_video
from gdrive_uploader import upload_video_to_gdrive, get_valid_access_token, cleanup_local_files

def main():
    print("=== BẮT ĐẦU QUY TRÌNH HOÀN THIỆN VIDEO CHUẨN XÁC ===")
    
    # 1. Ghép 9 clip trimmed
    clips = [TRIMMED_DIR / f"trimmed_sc_{i}.mp4" for i in range(1, 10)]
    for idx, c in enumerate(clips, 1):
        if not c.exists():
            raise FileNotFoundError(f"Không tìm thấy clip phân cảnh: {c}")
        cmd_d = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(c)]
        d = float(subprocess.check_output(cmd_d).decode().strip())
        print(f"[*] Cảnh {idx}: {d:.3f}s")
        
    concat_list = TRIMMED_DIR / "concat_perfect.txt"
    with open(concat_list, "w", encoding="utf-8") as f:
        for c in clips:
            f.write(f"file '{c.resolve().as_posix()}'\n")
            
    raw_merged = TASK_DIR / "merged_9scenes_raw.mp4"
    print("\n[*] [1/5] Đang ghép 9 cảnh thành video thô...")
    cmd_cat = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(concat_list),
        "-c", "copy",
        str(raw_merged)
    ]
    subprocess.run(cmd_cat, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # 2. Xây dựng danh sách phrases cho Karaoke Subtitles (tính toán chính xác theo timeline 1.1x)
    # Tốc độ 1.1x -> thời gian hiển thị = thời gian thô / 1.1
    # Danh sách phrases: (start_t, end_t, line1_words, line2_words)
    phrases = [
        # Scene 1: 0.00s -> 9.89s
        (0.20, 3.20, ["ĐÀN", "ÔNG", "ĐI", "TIỆC"], ["SỢ", "NHẤT", "VỢ", "LÀM", "MẤT", "MẶT!"]),
        (3.30, 6.20, ["NHƯNG", "MẤY", "AI", "THẤU"], ["VẺ", "NHĂN", "NHÓ", "U", "ÁM", "NÀY"]),
        (6.30, 9.70, ["LẠI", "BẮT", "NGUỒN", "TỪ", "GÓC", "KHUẤT"], ["TÍCH", "HÀN", "LẠNH", "BUỐT", "BÊN", "DƯỚI!"]),
        
        # Scene 2: 9.89s -> 18.22s
        (10.10, 14.50, ["ỦA", "BẰNG", "TUỔI", "BA", "MƯƠI", "HAI", "HẾT"], ["MÀ", "SAO", "CHỊ", "LINH", "ĐỨNG", "CO", "RO", "NGOÀI", "GIÓ"]),
        (14.60, 18.00, ["BÊN", "DƯỚI", "ẨM", "ƯƠNG", "BỐC", "MÙI"], ["TUI", "NÀO", "DÁM", "BƯỚC", "VÔ", "ĐÁM", "ĐÔNG!"]),
        
        # Scene 3: 18.22s -> 28.98s
        (18.50, 24.50, ["TRỜI", "ĐẤT,", "MẶC", "ĐẦM", "ĐẸP", "ĐI", "TÂN", "GIA", "SẾP"], ["MÀ", "NGƯỜI", "NGỢM", "CỨ", "HẦM", "BÍ", "NGAI", "NGÁI", "KHÓ", "CHỊU!"]),
        (24.70, 28.80, ["CHỒNG", "RUỘT", "MÀ", "NHĂN", "MŨI", "LÙI", "LẠI"], ["NHƯ", "NÉ", "NGƯỜI", "DƯNG", "NƯỚC", "LÃ!"]),
        
        # Scene 4: 28.98s -> 38.18s
        (29.20, 34.00, ["NHÌN", "VỢ", "NGƯỜI", "TA", "RẠNG", "RỠ", "PHÁT", "HAM"], ["LẦN", "SAU", "TIỆC", "LỚN", "CHẮC", "ANH", "ĐI", "MỘT", "MÌNH!"]),
        (34.20, 38.00, ["MỘT", "CÂU", "DỌA", "GẠCH", "TÊN", "VỢ"], ["KHỎI", "THẾ", "GIỚI", "CỦA", "ỔNG!"]),
        
        # Scene 5: 38.18s -> 44.81s
        (38.40, 41.50, ["TRỐN", "GÓC", "TỐI", "TỦI", "THÂN", "CHI", "EM!"], ["ĐÀN", "BÀ", "ĐỂ", "BỤNG", "DƯỚI", "TÍCH", "HÀN", "LẠNH", "NGẮT"]),
        (41.60, 44.60, ["VỚI", "MÙI", "BÍ", "BÁCH", "LÀ", "ĐẨY", "CHỒNG", "RA", "XA"], ["DÙNG", "LIỀN", "HỘP", "SNOW", "LOTUS", "NÀY", "NGHE", "CHỊ!"]),
        
        # Scene 6: 44.81s -> 55.91s
        (45.10, 48.00, ["ĐANG", "GIỮA", "BUỔI", "TIỆC", "VẦY"], ["MIẾNG", "MỎNG", "XÍU", "ĂN", "THUA", "HÔNG", "CHỊ?"]),
        (48.20, 52.00, ["CÔNG", "NGHỆ", "ĐAN", "MẠCH", "DƯỠNG", "KÉP"], ["BẢY", "TINH", "CHẤT", "VỚI", "BẢY", "THẢO", "MỘC", "HOA", "TUYẾT", "LIÊN"]),
        (52.10, 55.70, ["HỒNG", "HOA", "TRONG", "LÕI", "BỘT", "MỊN"], ["HỔNG", "VÓN", "CỤC", "ĐÓ", "CƯNG!"]),
        
        # Scene 7: 55.91s -> 64.43s
        (56.20, 60.50, ["NHIỆT", "ĐỘ", "CƠ", "THỂ", "BA", "MƯƠI", "BẢY", "ĐỘ"], ["GIÚP", "THẨM", "THẤU", "ĐƯƠNG", "QUY,", "ÍCH", "MẪU,", "THỤC", "ĐỊA"]),
        (60.60, 64.20, ["HỖ", "TRỢ", "LÀM", "ẤM", "DỊU", "DÀNG"], ["GIÚP", "GIẢM", "MÙI", "THOÁNG", "SẠCH", "SUỐT", "BUỔI", "TIỆC!"]),
        
        # Scene 8: 64.43s -> 75.34s
        (64.70, 70.00, ["ỦA", "VỢ", "VÔ", "SẢNH", "HỒI", "NÀO", "MÀ", "DA", "HỒNG", "HÀO"], ["ĐỨNG", "SÁT", "NGHE", "THOẢNG", "HƯƠNG", "THẢO", "MỘC", "SANG", "DỮ!"]),
        (70.20, 75.10, ["BÊN", "TRONG", "ẤM", "ÊM", "THOÁNG", "NHẸ"], ["THÌ", "THẦN", "THÁI", "TỰ", "KHẮC", "TỎA", "SÁNG", "THÔI", "ANH!"]),
        
        # Scene 9: 75.34s -> 83.52s
        (75.60, 79.50, ["ĐỪNG", "TIẾC", "TIỀN", "LẺ", "BỎ", "BÊ", "GÓC", "KHUẤT"], ["RỒI", "NƠM", "NỚP", "SỢ", "CHỒNG", "ĐI", "TIỆC", "MỘT", "MÌNH!"]),
        (79.70, 83.30, ["GÓI", "HAI", "MIẾNG", "GỌN", "NHẸ", "ĐANG", "ƯU", "ĐÃI", "GIÁ", "HỜI"], ["BẤM", "GIỎ", "HÀNG", "CHỐT", "LIỀN", "NGHEN!"])
    ]
    
    ass_path = TASK_DIR / "cottonday_karaoke.ass"
    print("\n[*] [2/5] Đang tạo file phụ đề Karaoke .ass chuẩn Roboto Black...")
    generate_karaoke_ass_file(phrases, ass_path, lead_in=0.35)
    print(f"[✓] Đã tạo file phụ đề: {ass_path} ({ass_path.stat().st_size} bytes)")
    
    # 3. Tăng tốc 1.1x và burn phụ đề Karaoke
    print("\n[*] [3/5] Đang tăng tốc 1.1x và burn phụ đề Karaoke...")
    speed_sub_out = TASK_DIR / "final_speed_subtitles.mp4"
    
    # Tăng tốc trước
    temp_speed = TASK_DIR / "_temp_speed_1.1.mp4"
    cmd_speed = [
        "ffmpeg", "-y", "-i", str(raw_merged),
        "-filter_complex", "[0:v]setpts=PTS/1.1[v];[0:a]atempo=1.1[a]",
        "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-crf", "18", "-preset", "fast",
        "-c:a", "aac", "-b:a", "192k",
        str(temp_speed)
    ]
    subprocess.run(cmd_speed, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # Burn phụ đề
    esc_ass = str(ass_path.resolve()).replace("\\", "/").replace(":", "\\:")
    esc_fonts = str(FONTS_DIR.resolve()).replace("\\", "/").replace(":", "\\:")
    cmd_sub = [
        "ffmpeg", "-y", "-i", str(temp_speed),
        "-vf", f"subtitles='{esc_ass}':fontsdir='{esc_fonts}'",
        "-c:v", "libx264", "-crf", "18", "-preset", "fast",
        "-c:a", "copy",
        str(speed_sub_out)
    ]
    subprocess.run(cmd_sub, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    temp_speed.unlink(missing_ok=True)
    print(f"[✓] Hoàn tất tăng tốc 1.1x và burn phụ đề: {speed_sub_out.stat().st_size / (1024*1024):.2f} MB")
    
    # 4. Gắn Footer Disclaimer 2 dòng sát đáy
    print("\n[*] [4/5] Đang gắn Footer Disclaimer 2 dòng...")
    final_output = PROJECT_DIR / "outputs" / "final_merged_video_1080p.mp4"
    final_output.parent.mkdir(parents=True, exist_ok=True)
    apply_footer_to_video(speed_sub_out, final_output)
    print(f"[✓] Hoàn tất video thành phẩm có Footer & Karaoke: {final_output.stat().st_size / (1024*1024):.2f} MB")
    
    # Copy sang storage_dir để phục vụ web app
    shutil_dest = TASK_DIR / "final_merged_video.mp4"
    import shutil
    shutil.copy2(final_output, shutil_dest)
    
    # 5. Upload lên Google Drive
    print("\n[*] [5/5] Đang upload lên Google Drive (Folder 1LQfVRoejxpoQLjgR_piVd1TuNUEH_Hra)...")
    custom_filename = "Series Cottonday - Mui Am Uong Ngoai Ban Cong (Thao Dien Saigon).mp4"
    gdrive_res = upload_video_to_gdrive(final_output, custom_filename=custom_filename)
    print(f"[✓] Link Google Drive View: {gdrive_res['view_link']}")
    print(f"[✓] Link Google Drive Direct Download: {gdrive_res['download_link']}")
    
    # 6. Dọn dẹp các file video nặng trên local
    print("\n[*] Đang giải phóng bộ nhớ local...")
    freed = cleanup_local_files(
        TASK_DIR, 
        PROJECT_DIR / "outputs" / "final_merged_video_1080p.mp4",
        patterns=("*.mp4",)
    )
    print(f"[✓] Tổng bộ nhớ giải phóng: {freed / (1024*1024):.2f} MB")
    
    print("\n============================================================")
    print("HOÀN TẤT XUẤT SẮC 100%!")
    print(f"File Google Drive: {custom_filename}")
    print(f"Link: {gdrive_res['view_link']}")
    print("============================================================")
    return gdrive_res

if __name__ == "__main__":
    main()
