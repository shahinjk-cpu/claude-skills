---
name: invidious
description: >
  Private YouTube front-end & API integration. Query videos, extract transcripts, stream audio/video, and bypass tracking, ads, and API quota limits without an official Google API key.
metadata:
  version: "1.0.0"
  category: content_media
  triggers: invidious, youtube private, youtube api alternative, scrape youtube, transcript without api
---

# Invidious — Private YouTube API & Media Pipeline

Integrates with public and self-hosted Invidious instances to search YouTube, retrieve video metadata, fetch subtitles/transcripts, and extract direct media streams without tracking, ads, or Google API quotas.

## Capabilities
- **Search & Discovery**: Query YouTube videos, channels, and playlists via Invidious REST API.
- **Transcript Extraction**: Fetch complete timestamped closed captions (VTT / SRT / JSON) without video downloads.
- **Audio/Video Direct URLs**: Obtain raw media stream URLs for audio processing, local playback, or Whisper transcription.
- **Privacy & Rate-Limit Bypassing**: Rotate across public Invidious instances or connect to a local self-hosted instance.

## Operating Protocol

### 1. Invidious API Endpoints
Default public instance or self-hosted endpoint: `http://localhost:3000` or public instances:
- Video info: `GET /api/v1/videos/:id`
- Search: `GET /api/v1/search?q=:query&type=video`
- Captions: `GET /api/v1/captions/:id`
- Channel: `GET /api/v1/channels/:id`

### 2. Fetching Video Transcripts with Python
```python
import requests

def get_transcript(video_id, instance="https://inv.nadeko.net"):
    url = f"{instance}/api/v1/captions/{video_id}"
    resp = requests.get(url, timeout=10)
    if resp.status_code == 200:
        captions = resp.json()
        return captions
    return None
```

### 3. Self-Hosting via Docker
```bash
docker run -d -p 3000:3000 --name invidious quay.io/invidious/invidious:latest
```
