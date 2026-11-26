"""
Google Drive OAuth 2.0 Setup & Exchange Script
Sử dụng GOOGLE_CLIENT_ID & GOOGLE_CLIENT_SECRET có sẵn trên hệ thống
để xin quyền Google Drive (scope: drive.file) và lưu refresh_token vĩnh viễn.
"""
import sys
import json
import urllib.parse
import urllib.request
from pathlib import Path

import os

CLIENT_ID = os.environ.get("GDRIVE_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("GDRIVE_CLIENT_SECRET", "")
REDIRECT_URI = "https://video.plzmail.net"
TOKEN_FILE = Path(__file__).resolve().parent.parent / "configs" / "gdrive_token.json"

def get_auth_url():
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": "https://www.googleapis.com/auth/drive.file",
        "access_type": "offline",
        "prompt": "consent"
    }
    return f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"

def exchange_code_for_tokens(code_or_url: str):
    code = code_or_url.strip()
    if "code=" in code:
        parsed = urllib.parse.urlparse(code)
        query = urllib.parse.parse_qs(parsed.query)
        if "code" in query:
            code = query["code"][0]
        else:
            code = code.split("code=")[1].split("&")[0]

    token_url = "https://oauth2.googleapis.com/token"
    data = urllib.parse.urlencode({
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT_URI
    }).encode("utf-8")

    req = urllib.request.Request(token_url, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req) as resp:
            tokens = json.loads(resp.read().decode("utf-8"))
            TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
            TOKEN_FILE.write_text(json.dumps(tokens, indent=2), encoding="utf-8")
            print(f"[✓] Đã lưu token thành công vào: {TOKEN_FILE}")
            print(f"[✓] Có refresh_token: {'refresh_token' in tokens}")
            return tokens
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8")
        print(f"[-] Lỗi đổi token: {e.code} - {err_msg}")
        return None

if __name__ == "__main__":
    if len(sys.argv) > 1:
        exchange_code_for_tokens(sys.argv[1])
    else:
        print("Auth URL:")
        print(get_auth_url())
