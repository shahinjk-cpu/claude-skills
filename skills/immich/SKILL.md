---
name: immich
description: >
  Self-hosted photo and video management solution. Query assets, trigger face recognition, manage albums, perform semantic visual search, and automate photo backups via Immich REST API.
metadata:
  version: "1.0.0"
  category: content_media
  triggers: immich, photo backup, google photos alternative, semantic image search, self-hosted gallery
---

# Immich — Self-Hosted High-Performance Photo Management

Integrates with an Immich server for asset indexing, CLIP-based natural language semantic image search, face clustering, album synchronization, and metadata extraction.

## Features
- **Semantic Search**: Find photos using natural language queries ("red sports car on mountain road", "sunset on the beach").
- **Asset Metadata**: Query EXIF data, GPS coordinates, camera parameters, and facial tags.
- **Album & Tag Management**: Programmatically organize assets into smart albums.
- **Deduplication**: SHA1/checksum matching to prevent duplicate uploads.

## API Usage

### Authentication
Include API key in request header: `x-api-key: <IMMICH_API_KEY>`.

### Python Semantic Search
```python
import requests

def search_photos(query, api_key, base_url="http://localhost:2283"):
    url = f"{base_url}/api/search/smart"
    headers = {"x-api-key": api_key, "Content-Type": "application/json"}
    payload = {"query": query}
    resp = requests.post(url, json=payload, headers=headers)
    return resp.json()
```
