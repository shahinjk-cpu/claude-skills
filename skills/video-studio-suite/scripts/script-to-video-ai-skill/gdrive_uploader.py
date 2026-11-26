"""
Google Drive Uploader for Pipeline Outputs
Tự động làm mới access_token bằng refresh_token từ gdrive_token.json
và upload video thành phẩm vào đúng thư mục chỉ định:
Folder ID: 1LQfVRoejxpoQLjgR_piVd1TuNUEH_Hra (TUYỆT ĐỐI KHÔNG UPLOAD LUNG TUNG)
"""
import os
import sys
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

CLIENT_ID = os.environ.get("GDRIVE_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("GDRIVE_CLIENT_SECRET", "")
TARGET_FOLDER_ID = os.environ.get("GDRIVE_TARGET_FOLDER_ID", "1LQfVRoejxpoQLjgR_piVd1TuNUEH_Hra")

BASE_DIR = Path(__file__).resolve().parent.parent
TOKEN_FILE = BASE_DIR / "configs" / "gdrive_token.json"

def get_valid_access_token() -> str:
    if not TOKEN_FILE.exists():
        raise FileNotFoundError(f"Không tìm thấy file token tại: {TOKEN_FILE}")
    
    tokens = json.loads(TOKEN_FILE.read_text(encoding="utf-8"))
    refresh_token = tokens.get("refresh_token")
    if not refresh_token:
        raise ValueError("Không tìm thấy refresh_token trong gdrive_token.json")

    # Luôn refresh để lấy access_token mới nhất (hết hạn sau 1h)
    token_url = "https://oauth2.googleapis.com/token"
    payload = urllib.parse.urlencode({
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token"
    }).encode("utf-8")

    req = urllib.request.Request(token_url, data=payload, headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req) as resp:
        fresh = json.loads(resp.read().decode("utf-8"))
        tokens["access_token"] = fresh["access_token"]
        tokens["expires_in"] = fresh.get("expires_in", 3600)
        TOKEN_FILE.write_text(json.dumps(tokens, indent=2), encoding="utf-8")
        return fresh["access_token"]

def upload_video_to_gdrive(file_path: Path, folder_id: str = TARGET_FOLDER_ID, custom_filename: str = None) -> dict:
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"File không tồn tại: {file_path}")

    filename = custom_filename or file_path.name
    file_size = file_path.stat().st_size
    print(f"[*] Đang chuẩn bị upload lên Google Drive: {filename} ({file_size / (1024*1024):.2f} MB)...")
    print(f"[*] Thư mục đích: {folder_id}")

    access_token = get_valid_access_token()

    # 1. Khởi tạo Resumable Upload Session
    metadata = {
        "name": filename,
        "parents": [folder_id]
    }
    meta_bytes = json.dumps(metadata).encode("utf-8")

    init_url = "https://www.googleapis.com/upload/drive/v3/files?uploadType=resumable"
    init_headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; charset=UTF-8",
        "X-Upload-Content-Type": "video/mp4",
        "X-Upload-Content-Length": str(file_size)
    }

    init_req = urllib.request.Request(init_url, data=meta_bytes, headers=init_headers, method="POST")
    with urllib.request.urlopen(init_req) as init_resp:
        upload_url = init_resp.headers.get("Location")

    if not upload_url:
        raise RuntimeError("Google Drive không trả về upload session Location")

    # 2. Upload file theo chunk (16MB mỗi chunk)
    chunk_size = 16 * 1024 * 1024
    uploaded = 0
    file_id = None

    with open(file_path, "rb") as f:
        while uploaded < file_size:
            chunk = f.read(chunk_size)
            c_len = len(chunk)
            range_header = f"bytes {uploaded}-{uploaded + c_len - 1}/{file_size}"
            
            headers = {
                "Content-Length": str(c_len),
                "Content-Range": range_header,
                "Content-Type": "video/mp4"
            }
            req = urllib.request.Request(upload_url, data=chunk, headers=headers, method="PUT")
            
            pct = ((uploaded + c_len) / file_size) * 100
            print(f"[*] Uploading: {range_header} ({pct:.1f}%)...")
            
            try:
                with urllib.request.urlopen(req) as resp:
                    if resp.status in [200, 201]:
                        result = json.loads(resp.read().decode("utf-8"))
                        file_id = result.get("id")
                        break
            except urllib.error.HTTPError as e:
                if e.code == 308: # Resume incomplete
                    pass
                else:
                    raise e
            uploaded += c_len

    if not file_id:
        raise RuntimeError("Upload xong nhưng không nhận được file_id từ Google Drive")

    # 3. Chia sẻ quyền đọc công khai cho link (Anyone with link can view)
    try:
        perm_url = f"https://www.googleapis.com/drive/v3/files/{file_id}/permissions"
        perm_data = json.dumps({"role": "reader", "type": "anyone"}).encode("utf-8")
        perm_req = urllib.request.Request(
            perm_url, data=perm_data,
            headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
        )
        urllib.request.urlopen(perm_req)
    except Exception as pe:
        print(f"[-] Cảnh báo share quyền: {pe}")

    view_link = f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"
    download_link = f"https://drive.google.com/uc?export=download&id={file_id}"
    folder_link = f"https://drive.google.com/drive/folders/{folder_id}"

    print(f"\n[✓] UPLOAD GOOGLE DRIVE THÀNH CÔNG 100%!")
    print(f"ID: {file_id}")
    print(f"Link Xem/Tải: {view_link}")
    print(f"Link Download Trực Tiếp: {download_link}")

    return {
        "file_id": file_id,
        "name": filename,
        "view_link": view_link,
        "download_link": download_link,
        "folder_link": folder_link
    }

def rename_gdrive_file(file_id: str, new_name: str) -> dict:
    """Đổi tên file trên Google Drive qua API PATCH."""
    access_token = get_valid_access_token()
    url = f"https://www.googleapis.com/drive/v3/files/{file_id}"
    data = json.dumps({"name": new_name}).encode("utf-8")
    req = urllib.request.Request(
        url, data=data,
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
        method="PATCH"
    )
    with urllib.request.urlopen(req) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        print(f"[✓] Đã đổi tên file Google Drive thành: {res.get('name')}")
        return res

def cleanup_local_files(*paths_or_dirs, patterns=("*.mp4", "*.m4a")) -> int:
    """Xóa các file video nặng sau khi đã upload Google Drive an toàn để giải phóng bộ nhớ VPS/local."""
    freed = 0
    for item in paths_or_dirs:
        if not item:
            continue
        p = Path(item)
        if p.is_file() and p.exists():
            try:
                sz = p.stat().st_size
                p.unlink()
                freed += sz
                print(f"[*] Đã xóa file local giải phóng bộ nhớ: {p.name} ({sz / (1024*1024):.2f} MB)")
            except Exception as e:
                print(f"[-] Không thể xóa {p}: {e}")
        elif p.is_dir() and p.exists():
            for pat in patterns:
                for f in p.glob(pat):
                    try:
                        sz = f.stat().st_size
                        f.unlink()
                        freed += sz
                        print(f"[*] Đã xóa file tạm local: {f.name} ({sz / (1024*1024):.2f} MB)")
                    except Exception as e:
                        print(f"[-] Không thể xóa {f}: {e}")
    print(f"[✓] Tổng dung lượng local đã giải phóng: {freed / (1024*1024):.2f} MB")
    return freed

if __name__ == "__main__":
    test_file = Path("kich_ban_to_video/projects/cottonday_rooftop_bbq/outputs/final_merged_video_1080p.mp4")
    if len(sys.argv) > 1:
        test_file = Path(sys.argv[1])
    res = upload_video_to_gdrive(test_file)
    print(json.dumps(res, indent=2))
