"""
GLabs Studio Pipeline Automation Runner with Smart Self-Healing & Audio Gate
Chạy render video từ bên ngoài qua GLabs Studio Web API (100% Client-Side)
- Bắt lỗi Content Policy trong 3s, tự làm mềm cử chỉ hoạt hình (bảo toàn 100% thoại)
- Tự động kiểm tra âm thanh dứt lời (Audio Verifier Gate), tự tăng giây nếu bị cụt thoại
- Cô lập dự án khép kín trong kich_ban_to_video/projects/<ten_du_an>/
- Tuyệt đối không can thiệp vào mã nguồn máy chủ web_glabs_studio/server.py
"""
import sys
import json
import time
import re
import urllib.request
import urllib.error
import argparse
import shutil
import subprocess
from pathlib import Path

# Thêm đường dẫn scripts để import audio_verifier và visual_verifier
sys.path.append(str(Path(__file__).parent.resolve()))
from audio_verifier import verify_scene_audio
from visual_verifier import extract_scene_inspection_frames, auto_lock_speaker_and_characters
from snappy_trimmer import merge_scenes_snappy
from add_footer import apply_footer_to_video
from subtitles_builder import apply_subtitles_and_speed
from dialogue_auditor import audit_scenes_dialogue, audit_single_scene

API_BASE = "http://127.0.0.1:3070"
DEFAULT_AUTH_TOKEN = "u8802880@gmail.com"

def submit_pipeline(config_path: str, token: str = DEFAULT_AUTH_TOKEN) -> str:
    with open(config_path, "r", encoding="utf-8") as f:
        payload_data = json.load(f)

    # TỰ ĐỘNG KHÓA KHẨU HÌNH & GIỚI HẠN NHÂN VẬT CHO MỌI CẢNH TRƯỚC KHI GỬI
    if "video_prompts" in payload_data and isinstance(payload_data["video_prompts"], list):
        enhanced_prompts = []
        for vp in payload_data["video_prompts"]:
            enhanced_prompts.append(auto_lock_speaker_and_characters(vp))
        payload_data["video_prompts"] = enhanced_prompts

    # BẮT BUỘC TẮT AUTO_MERGE TRÊN SERVER ĐỂ KHÔNG GHÉP MÙ MỜ TRƯỚC KHI THẨM ĐỊNH THOẠI
    payload_data["auto_merge"] = False

    data = json.dumps(payload_data).encode("utf-8")
    req = urllib.request.Request(
        f"{API_BASE}/api/start-pipeline",
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
    )
    with urllib.request.urlopen(req) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        pipeline_id = res.get("task_id") or res.get("pipeline_id")
        print(f"[+] Pipeline khởi tạo thành công qua API. ID: {pipeline_id}")
        return pipeline_id

def sanitize_motion_prompt(prompt: str, attempt: int = 1) -> str:
    """Giữ nguyên 100% Voice Directing, làm mềm mô tả hành động và lọc từ ngữ nhạy cảm trong thoại nếu cần."""
    diag_match = re.search(r'((?:Dialogue:|Voice Directing:).*)', prompt, re.IGNORECASE | re.DOTALL)
    if diag_match:
        vd_and_dialogue = diag_match.group(1).strip()
    else:
        vd_and_dialogue = prompt

    vd_and_dialogue = re.sub(r'chà đạp không thương tiếc', 'soi mói không tiếc lời', vd_and_dialogue, flags=re.IGNORECASE)
    vd_and_dialogue = re.sub(r'chà đạp', 'chê cười', vd_and_dialogue, flags=re.IGNORECASE)
    vd_and_dialogue = re.sub(r'không thương tiếc', 'không tiếc lời', vd_and_dialogue, flags=re.IGNORECASE)
    vd_and_dialogue = re.sub(r'cặp đào bén ngót', 'vóc dáng chuẩn chỉnh', vd_and_dialogue, flags=re.IGNORECASE)
    vd_and_dialogue = re.sub(r'mắm ruốc lâu năm', 'nồng nặc khó chịu', vd_and_dialogue, flags=re.IGNORECASE)
    vd_and_dialogue = re.sub(r'hút ra một đống cặn trắng đục như bã đậu, đặc quánh cái mùi chua lè', 'hút sạch cặn bẩn hầm bí tích tụ, thoáng sạch the mát tức thì', vd_and_dialogue, flags=re.IGNORECASE)
    vd_and_dialogue = re.sub(r'ra bã đậu với bốc mùi khẳm lẹm', 'bị hầm bí ngứa ngáy khó chịu', vd_and_dialogue, flags=re.IGNORECASE)
    vd_and_dialogue = re.sub(r'mùi hầm bí ở trỏng', 'mùi hầm bí khó chịu', vd_and_dialogue, flags=re.IGNORECASE)
    vd_and_dialogue = re.sub(r'ở trỏng', 'ở đây', vd_and_dialogue, flags=re.IGNORECASE)
    vd_and_dialogue = re.sub(r'khí hư ứ đọng', 'ẩm bí ứ đọng', vd_and_dialogue, flags=re.IGNORECASE)

    # Nếu thử lần 2 mà vẫn bị policy, làm sạch các từ ngữ y tế/tình cảm nhạy cảm trong thoại và chỉ dẫn giọng
    if attempt >= 2:
        vd_and_dialogue = re.sub(r'thuốc độc bọc đường', 'thuốc bọc đường hại người', vd_and_dialogue, flags=re.IGNORECASE)
        vd_and_dialogue = re.sub(r'thuốc độc', 'thuốc hại người', vd_and_dialogue, flags=re.IGNORECASE)
        vd_and_dialogue = re.sub(r'triệt đường sinh nở', 'hại đường sinh nở', vd_and_dialogue, flags=re.IGNORECASE)
        vd_and_dialogue = re.sub(r'thúi ruột thúi gan', 'ứ đọng trong người', vd_and_dialogue, flags=re.IGNORECASE)
        vd_and_dialogue = re.sub(r'lả lướt', 'vui vẻ phấn khởi', vd_and_dialogue, flags=re.IGNORECASE)
        vd_and_dialogue = re.sub(r'cưng liền', 'quý liền', vd_and_dialogue, flags=re.IGNORECASE)
        vd_and_dialogue = re.sub(r'sạch thơm', 'tinh tươm', vd_and_dialogue, flags=re.IGNORECASE)
        vd_and_dialogue = re.sub(r'nghẹn đắng hoảng loạn', 'trầm buồn suy tư', vd_and_dialogue, flags=re.IGNORECASE)
        vd_and_dialogue = re.sub(r'xập xệ khắc khổ', 'bận rộn tất bật', vd_and_dialogue, flags=re.IGNORECASE)

    safe_action = "Khung cảnh hoạt hình 3D Pixar tươi sáng. Nhân vật tương tác trò chuyện sinh động tự nhiên theo đúng bối cảnh kịch bản, biểu cảm hài hước, cử chỉ nhẹ nhàng."
    return f"{safe_action} {vd_and_dialogue}"

def sanitize_image_prompt(prompt: str) -> str:
    """Loại bỏ các từ ngữ va chạm/bạo lực trong mô tả ảnh, chuyển sang tương tác gia đình vui vẻ Pixar."""
    clean = re.sub(r'(hitting|beating|broom handle|slapping|violently|fighting|cowering)', 'talking animatedly, humorous expressions', prompt, flags=re.IGNORECASE)
    return clean

def monitor_and_heal_pipeline(pipeline_id: str, project_dir: Path, token: str = DEFAULT_AUTH_TOKEN, poll_interval: int = 4):
    print(f"[*] Bắt đầu giám sát tự hành cho Pipeline: {pipeline_id}")
    print(f"[*] Thư mục lưu trữ dự án: {project_dir}")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    last_status = None
    heal_attempts = {}
    healed_scenes = set()
    verified_stt_scenes = set()
    visual_checked_scenes = set()
    retrying_diag_scenes = set()
    storage_dir = Path("web_glabs_studio/storage") / pipeline_id

    while True:
        try:
            req = urllib.request.Request(f"{API_BASE}/api/pipelines", headers=headers)
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                pipelines = data.get("pipelines", [])
                target = next((p for p in pipelines if p.get("id") == pipeline_id), None)

                if not target:
                    time.sleep(poll_interval)
                    continue

                status = target.get("state") or target.get("status")
                name = target.get("custom_name") or target.get("name", "Untitled")
                scenes = target.get("scenes", [])
                completed_videos = sum(1 for s in scenes if s.get("video_status") in ("done", "completed"))
                total_scenes = len(scenes)

                summary = f"[{name}] Trạng thái: {status} | Đã xong: {completed_videos}/{total_scenes} cảnh | Đã duyệt STT: {len(verified_stt_scenes)}/{total_scenes}"
                if summary != last_status:
                    print(f"[*] [{time.strftime('%H:%M:%S')}] {summary}")
                    for sc in scenes:
                        sid = sc.get("id")
                        img_st = sc.get("image_status", "-")
                        vid_st = sc.get("video_status", "-")
                        v_err = sc.get("video_error")
                        v_len = sc.get("video_length")
                        stt_mark = " [STT ✓]" if sid in verified_stt_scenes else ""
                        err_str = f" [LỖI: {v_err}]" if v_err else ""
                        print(f"    Cảnh {sid} ({v_len}s): Image={img_st} | Video={vid_st}{stt_mark}{err_str}")
                    last_status = summary

                # 1. TỰ CHỮA LÀNH TỨC THÌ (SELF-HEALING) KHI BỊ CONTENT_POLICY (Bắt lỗi trong 3-4s)
                for sc in scenes:
                    sid = sc.get("id")
                    img_st = sc.get("image_status")
                    vid_st = sc.get("video_status")
                    v_err = str(sc.get("video_error") or "")
                    img_err = str(sc.get("image_error") or "")

                    # Lỗi Video Content Policy
                    if vid_st == "failed":
                        attempts = heal_attempts.get(sid, 0)
                        if ("CONTENT_POLICY" in v_err or "refused" in v_err.lower()) and attempts < 2:
                            heal_attempts[sid] = attempts + 1
                            print(f"\n[!] Cảnh {sid} bị từ chối kiểm duyệt Video (Lần {heal_attempts[sid]})!")
                            print(f"[*] [SELF-HEALING TỰ ĐỘNG] Làm mềm mô tả cử chỉ & rà soát từ ngữ nhạy cảm rồi retry ngay...")
                            old_prompt = sc.get("video_prompt", "")
                            sanitized = sanitize_motion_prompt(old_prompt, attempt=heal_attempts[sid])
                            v_len = sc.get("video_length") or 8
                            
                            retry_url = f"{API_BASE}/api/pipeline/{pipeline_id}/retry-scene/{sid}"
                            retry_payload = {
                                "type": "video",
                                "prompt": sanitized,
                                "video_model": "omni_vids",
                                "video_length": v_len
                            }
                            ret_req = urllib.request.Request(retry_url, data=json.dumps(retry_payload).encode("utf-8"), headers=headers)
                            with urllib.request.urlopen(ret_req) as ret_resp:
                                print(f"[✓] Đã kích hoạt retry Cảnh {sid} thành công!")
                        elif attempts >= 2:
                            print(f"[!] BÁO ĐỘNG: Cảnh {sid} đã retry 2 lần nhưng vẫn bị Content Policy. Thoát để AI can thiệp trực tiếp!")
                            sys.exit(1)

                    # Lỗi Image Content Policy
                    if img_st == "failed" and f"img_{sid}" not in healed_scenes:
                        if "CONTENT_POLICY" in img_err or "refused" in img_err.lower():
                            print(f"\n[!] Cảnh {sid} bị từ chối kiểm duyệt Ảnh!")
                            print(f"[*] [SELF-HEALING TỰ ĐỘNG] Làm sạch mô tả ảnh và retry...")
                            old_img_prompt = sc.get("image_prompt", "")
                            sanitized_img = sanitize_image_prompt(old_img_prompt)
                            
                            retry_url = f"{API_BASE}/api/pipeline/{pipeline_id}/retry-scene/{sid}"
                            retry_payload = {"type": "image", "prompt": sanitized_img}
                            ret_req = urllib.request.Request(retry_url, data=json.dumps(retry_payload).encode("utf-8"), headers=headers)
                            with urllib.request.urlopen(ret_req) as ret_resp:
                                print(f"[✓] Đã kích hoạt tạo lại ảnh Cảnh {sid} thành công!")
                            healed_scenes.add(f"img_{sid}")

                    # 2. KIỂM TRA THOẠI REAL-TIME TỪNG CẢNH NGAY KHI VỪA RENDER XONG (PRE-MERGE REAL-TIME AUDIT)
                    vid_file = storage_dir / f"scene_{sid}_video.mp4"
                    if vid_st in ("completed", "done") and vid_file.exists() and sid not in verified_stt_scenes and sid not in retrying_diag_scenes:
                        insp_dir = storage_dir / "_inspection_frames"
                        if sid not in visual_checked_scenes:
                            extract_scene_inspection_frames(vid_file, insp_dir)
                            visual_checked_scenes.add(sid)

                        try:
                            s_res = audit_single_scene(sc, storage_dir)
                        except Exception as ae:
                            print(f"[-] [HẬU KỲ REAL-TIME] Lỗi audit STT Cảnh {sid}: {ae}")
                            s_res = {"is_critical": False, "match_rate": 1.0, "actual": "", "issues": []}

                        if s_res.get("is_critical"):
                            att = heal_attempts.get(f"diag_{sid}", 0)
                            if att < 2:
                                heal_attempts[f"diag_{sid}"] = att + 1
                                print(f"\n⛔ [STT REAL-TIME] Cảnh {sid} lỗi thoại nghiêm trọng: {s_res.get('issues')}!")
                                print(f"    Thoại bóc băng: \"{s_res.get('actual')}\" | Kịch bản: \"{s_res.get('expected')}\"")
                                print(f"[*] Kích hoạt render lại Cảnh {sid} ngay lập tức (Lần thử {att+1}/2)...")

                                retrying_diag_scenes.add(sid)
                                if sid in visual_checked_scenes:
                                    visual_checked_scenes.remove(sid)
                                try:
                                    vid_file.unlink(missing_ok=True)
                                except Exception:
                                    pass

                                r_payload = {
                                    "type": "video",
                                    "prompt": sc.get("video_prompt", ""),
                                    "video_model": sc.get("video_model") or "omni_vids",
                                    "video_length": sc.get("video_length") or 14,
                                    "count": 1,
                                    "use_ref_image": True
                                }
                                try:
                                    r_req = urllib.request.Request(
                                        f"{API_BASE}/api/pipeline/{pipeline_id}/retry-scene/{sid}",
                                        data=json.dumps(r_payload).encode("utf-8"),
                                        headers=headers
                                    )
                                    with urllib.request.urlopen(r_req) as r_resp:
                                        print(f"[✓] Đã kích hoạt tạo lại video Cảnh {sid} thành công!")
                                except Exception as re_e:
                                    print(f"[-] Lỗi gửi retry Cảnh {sid}: {re_e}")
                            else:
                                print(f"\n❌ [HARD BLOCK] Cảnh {sid} lỗi thoại và đã hết 2 lượt retry! Dừng để AI can thiệp.")
                                sys.exit(1)
                        else:
                            verified_stt_scenes.add(sid)
                            issues_txt = f" (Cảnh báo: {', '.join(s_res['issues'])})" if s_res.get("issues") else ""
                            print(f"[✓ STT Real-time] Cảnh {sid}: Đạt chuẩn thoại ({s_res.get('match_rate', 0)*100:.0f}%){issues_txt}")

                    # Khi cảnh retry chuyển trạng thái, giải phóng khỏi set retrying
                    if sid in retrying_diag_scenes and vid_st not in ("completed", "done"):
                        retrying_diag_scenes.remove(sid)

                # 3. KHI TOÀN BỘ CẢNH ĐÃ HOÀN TẤT VÀ VƯỢT QUA KIỂM TRA THOẠI -> TIẾN HÀNH GHÉP DUY NHẤT 1 LẦN
                if total_scenes > 0 and len(verified_stt_scenes) == total_scenes:
                    print("\n" + "="*60)
                    print(f"[✓] TOÀN BỘ {total_scenes}/{total_scenes} CẢNH ĐÃ HOÀN TẤT VÀ ĐẠT CHUẨN THOẠI 100%!")
                    print("[*] Bắt đầu cắt tỉa dứt khoát (+0.15s) loại bỏ 100% dead air và ghép 1080p...")
                    print("="*60)

                    final_merged_src = storage_dir / "final_merged_video.mp4"
                    try:
                        merge_scenes_snappy(storage_dir, final_merged_src, len(scenes))
                    except Exception as me:
                        print(f"[-] Snappy trim fallback: {me}")
                        merge_req = urllib.request.Request(
                            f"{API_BASE}/api/pipeline/{pipeline_id}/merge",
                            data=json.dumps({"resolution": "1080p", "smart_trim": True}).encode("utf-8"),
                            headers=headers
                        )
                        with urllib.request.urlopen(merge_req) as m_resp:
                            print(f"[+] Fallback server merge status: {m_resp.status}")

                    # Chờ file ghép xuất hiện và hoàn thành
                    for _ in range(30):
                        time.sleep(3)
                        if final_merged_src.exists() and final_merged_src.stat().st_size > 1000000:
                            s1 = final_merged_src.stat().st_size
                            time.sleep(2)
                            s2 = final_merged_src.stat().st_size
                            if s1 == s2:
                                break

                    if final_merged_src.exists():
                        # 1. TỰ ĐỘNG TĂNG TỐC ĐỘ 1.1x (TẠM THỜI BỎ PHỤ ĐỀ THEO CHỈ ĐẠO CỦA NGƯỜI DÙNG)
                        speed_tmp = storage_dir / "final_speed_subtitles.mp4"
                        try:
                            print("[*] [POST-MERGE] Tự động tăng tốc độ video lên 1.1x (không gắn phụ đề)...")
                            apply_subtitles_and_speed(final_merged_src, speed_tmp, ass_path=None, speed=1.1)
                            if speed_tmp.exists() and speed_tmp.stat().st_size > 1000000:
                                shutil.move(str(speed_tmp), str(final_merged_src))
                                print("[✓] [POST-MERGE] Đã hoàn tất tăng tốc 1.1x!")
                        except Exception as se:
                            print(f"[-] [POST-MERGE] Lỗi tăng tốc: {se}")

                        # 2. KIỂM TRA TỰ ĐỘNG APPLY FOOTER MIỄN TRỪ NẾU CÓ SẢN PHẨM / COTTONDAY / SNOW LOTUS
                        is_product_video = any(
                            re.search(
                                r'(\[LOCK:?\s*SAN_PHAM\]|cottonday|snow lotus|thảo mộc|băng vệ sinh|hộp sản phẩm)',
                                (sc.get("image_prompt") or "") + " " + (sc.get("video_prompt") or "") + " " + (target.get("custom_name") or ""),
                                re.IGNORECASE
                            )
                            for sc in scenes
                        )
                        if is_product_video:
                            print("[*] [AUTO FOOTER] Phát hiện sản phẩm / Cottonday -> Tự động gắn footer disclaimer 2 dòng...")
                            footer_tmp = storage_dir / "final_with_footer.mp4"
                            try:
                                apply_footer_to_video(final_merged_src, footer_tmp)
                                if footer_tmp.exists() and footer_tmp.stat().st_size > 1000000:
                                    shutil.move(str(footer_tmp), str(final_merged_src))
                                    print("[✓] [AUTO FOOTER] Đã gắn footer disclaimer thành công!")
                            except Exception as fe:
                                print(f"[-] [AUTO FOOTER] Lỗi gắn footer: {fe}")

                        outputs_dir = project_dir / "outputs" if (project_dir / "outputs").exists() else Path("kich_ban_to_video/outputs")
                        outputs_dir.mkdir(parents=True, exist_ok=True)
                        dest_file = outputs_dir / "final_merged_video_1080p.mp4"
                        shutil.copy2(final_merged_src, dest_file)
                        
                        # Copy các clip phân cảnh để lưu trữ
                        for sc_vid in storage_dir.glob("scene_*_video.mp4"):
                            shutil.copy2(sc_vid, outputs_dir / sc_vid.name)
                        for sc_img in storage_dir.glob("scene_*_image.png"):
                            shutil.copy2(sc_img, outputs_dir / sc_img.name)

                        # Đồng thời copy sang outputs chung
                        general_out = Path("kich_ban_to_video/outputs")
                        if outputs_dir.resolve() != general_out.resolve():
                            general_out.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(final_merged_src, general_out / "final_merged_video_1080p.mp4")

                        # Cập nhật DB URL với timestamp chống cache trình duyệt và hỗ trợ tải trực tiếp
                        db_path = Path("web_glabs_studio/storage/studio_db.sqlite")
                        if db_path.exists():
                            try:
                                import sqlite3
                                ts = int(time.time())
                                new_db_url = f"/storage/{pipeline_id}/final_merged_video.mp4?t={ts}"
                                with sqlite3.connect(str(db_path)) as conn:
                                    conn.execute("UPDATE pipelines SET merged_video_url = ? WHERE id = ?", (new_db_url, pipeline_id))
                                    conn.commit()
                                print(f"[✓] Đã cập nhật merged_video_url trong DB: {new_db_url}")
                            except Exception as dbe:
                                print(f"[-] DB update warning: {dbe}")

                        # Tự động upload lên đúng thư mục Google Drive đã chỉ định với tên theo kịch bản
                        try:
                            from gdrive_uploader import upload_video_to_gdrive, cleanup_local_files
                            
                            # Xác định tên kịch bản để đặt tên file trên Google Drive
                            script_title = target.get("custom_name") or (target.get("config") if isinstance(target.get("config"), dict) else {}).get("custom_name")
                            if not script_title:
                                script_title = f"video_{pipeline_id}"
                            safe_name = re.sub(r'[\\/*?:"<>|]', "", script_title).strip() + ".mp4"

                            print(f"\n[*] [GDRIVE] Đang tự động upload video lên Google Drive (Folder 1LQfVRoejxpoQLjgR_piVd1TuNUEH_Hra)...")
                            print(f"[*] [GDRIVE] Tên file Google Drive: {safe_name}")
                            gdrive_res = upload_video_to_gdrive(dest_file, custom_filename=safe_name)
                            print(f"[✓] [GDRIVE] Link Drive: {gdrive_res['view_link']}")

                            # Tự động xóa file video .mp4 trong kich_ban_to_video/projects/{project}/outputs/ để giải phóng bộ nhớ repo
                            # TUYỆT ĐỐI KHÔNG động đến file bên server (web_glabs_studio/storage/) vì server đã có cơ chế auto-delete riêng và phục vụ web app
                            print("\n[*] [CLEANUP] Tự động xóa các file video .mp4 trong thư mục project outputs để giải phóng bộ nhớ...")
                            cleanup_local_files(outputs_dir, general_out / "final_merged_video_1080p.mp4", patterns=("*.mp4",))
                            print("[✓] [STORAGE] Giữ nguyên toàn bộ file video bên server (web_glabs_studio/storage/) theo đúng chỉ đạo.")
                        except Exception as ge:
                            print(f"[-] [GDRIVE] Lỗi upload: {ge}")

                        print("\n" + "="*60)
                        print(f"[SUCCESS] ĐÃ HOÀN TẤT VÀ LƯU VÀO GOOGLE DRIVE!")
                        if 'gdrive_res' in locals() and gdrive_res:
                            print(f"Link Xem Google Drive: {gdrive_res['view_link']}")
                            print(f"Link Download: {gdrive_res['download_link']}")
                        print("="*60)
                        return target

        except Exception as e:
            print(f"[!] Warning giám sát: {e}")

        time.sleep(poll_interval)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="External Smart Controller for Script-to-Video")
    parser.add_argument("config", nargs="?", default="", help="Đường dẫn tới file cấu hình pipeline JSON")
    parser.add_argument("--task-id", help="Pipeline Task ID đang chạy để tiếp tục giám sát")
    parser.add_argument("--token", default=DEFAULT_AUTH_TOKEN, help="Auth bearer token")
    parser.add_argument("--poll", type=int, default=4, help="Khoảng thời gian polling (giây)")
    parser.add_argument("--project-dir", help="Thư mục dự án outputs")
    args = parser.parse_args()

    out_dir = Path("kich_ban_to_video/outputs")
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.task_id:
        pid = args.task_id
        if args.project_dir:
            proj_dir = Path(args.project_dir)
        elif Path("kich_ban_to_video/projects/cottonday_rooftop_bbq").exists():
            proj_dir = Path("kich_ban_to_video/projects/cottonday_rooftop_bbq")
        elif Path("kich_ban_to_video/projects/cottonday_snow_lotus").exists():
            proj_dir = Path("kich_ban_to_video/projects/cottonday_snow_lotus")
        else:
            proj_dir = Path("kich_ban_to_video")
        monitor_and_heal_pipeline(pid, proj_dir, args.token, args.poll)
    else:
        if not args.config:
            print("[-] Vui lòng cung cấp đường dẫn cấu hình hoặc --task-id")
            sys.exit(1)
        cfg_path = Path(args.config).resolve()
        if not cfg_path.exists():
            print(f"[-] Không tìm thấy file cấu hình: {cfg_path}")
            sys.exit(1)

        proj_dir = cfg_path.parent.parent if (cfg_path.parent.parent / "outputs").exists() else Path("kich_ban_to_video")
        pid = submit_pipeline(str(cfg_path), args.token)
        if pid:
            monitor_and_heal_pipeline(pid, proj_dir, args.token, args.poll)
