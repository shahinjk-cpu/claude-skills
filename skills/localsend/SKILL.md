---
name: localsend
description: >
  Open-source cross-platform local file sharing via LocalSend protocol. Discover local network devices, send and receive files, text, and directories securely without internet access.
metadata:
  version: "1.0.0"
  category: general_tools
  triggers: localsend, local share, airdrop alternative, send file local network, wifi share
---

# LocalSend — Secure Local File & Message Sharing

Coordinates peer-to-peer file, folder, and clipboard transfers between local network devices (PC, Mac, Linux, Android, iOS) using the open LocalSend HTTPS/REST protocol without cloud reliance.

## Features
- **Local Network Discovery**: Uses multicast UDP (`224.0.0.167:53317`) for zero-config neighbor discovery.
- **Direct HTTPS Transfer**: End-to-end encrypted transfer with self-signed TLS certificates over port `53317`.
- **Headless & CLI Support**: Control transfers via LocalSend CLI, HTTP API, or automations.

## Protocol & Usage

### 1. LocalSend API Endpoints (Port 53317)
- **Info / Fingerprint**: `GET /api/localsend/v2/info`
- **Prepare Upload**: `POST /api/localsend/v2/prepare-upload`
- **Upload File**: `POST /api/localsend/v2/upload?sessionId={id}`
- **Send Text**: `POST /api/localsend/v2/text`

### 2. Checking Active Receiver
```powershell
curl http://localhost:53317/api/localsend/v2/info
```

### 3. Automated Sending Script
```python
import requests

def send_text_to_device(ip, message, port=53317):
    url = f"http://{ip}:{port}/api/localsend/v2/text"
    payload = {"text": message}
    return requests.post(url, json=payload, timeout=5)
```
