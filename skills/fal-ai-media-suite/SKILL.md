---
name: fal-ai-media-suite
description: Complete Fal.ai master client suite for generative AI models (Flux, Stable Diffusion, video generation, 3D generation, audio, and image upscaling).
---

# Fal.ai Generative Media Master Suite

Unified API workflows for generative image, video, 3D, and audio synthesis on Fal.ai.

## Endpoints & Capabilities
### 3D (`fal-3d`)
---
name: fal-3d
description: |
  Generate 3D models from text or images via fal.ai. Useful for game assets, AR previews, product mockups, and concept sculpting.
triggers:
  - "fal 3d"
  - "text to 3d"
  - "image to 3d"
  - "3d model gen"
  - "game asset 3d"
od:
  mode: image
  category: 3d-shaders
  upstream: "https://github.com/fal-ai-community/skills"
---

# fal-3d

> Curated from the fal.ai community team.

## What it does

Generate 3D models

### Ai Media (`fal-ai-media`)
---
name: fal-ai-media
description: Unified media generation via fal.ai MCP — image, video, and audio. Covers text-to-image (Nano Banana), text/image-to-video (Seedance, Kling, Veo 3), text-to-speech (CSM-1B), and video-to-audio (ThinkSound). Use when the user wants to generate images, videos, or audio with AI.
metadata:
  origin: ECC
---

# fal.ai Media Generation

> **Drift-prone skill.** fal.ai model IDs, pricing, inputs, and MCP tool names
> 

### Generate (`fal-generate`)
---
name: fal-generate
description: |
  Generate images and videos using fal.ai AI models. Production-grade catalogue covering Flux, SDXL, ideogram, and other community-hosted endpoints.
triggers:
  - "fal generate"
  - "fal.ai image"
  - "flux image"
  - "sdxl"
  - "ideogram"
od:
  mode: image
  category: image-generation
  upstream: "https://github.com/fal-ai-community/skills"
---

# fal-generate

> Curated from the fal.ai community team.

## W

### Image Edit (`fal-image-edit`)
---
name: fal-image-edit
description: |
  AI-powered image editing with style transfer, background removal, object removal, and inpainting via fal.ai hosted models.
triggers:
  - "fal image edit"
  - "inpaint"
  - "style transfer"
  - "background removal"
  - "object removal"
od:
  mode: image
  category: image-generation
  upstream: "https://github.com/fal-ai-community/skills"
---

# fal-image-edit

> Curated from the fal.ai community team.

## 

### Kling O3 (`fal-kling-o3`)
---
name: fal-kling-o3
description: |
  Generate images and videos with Kling O3 — Kling's most powerful model family — via fal.ai.
triggers:
  - "fal kling"
  - "kling o3"
  - "kling video"
  - "kling image"
od:
  mode: video
  category: video-generation
  upstream: "https://github.com/fal-ai-community/skills"
---

# fal-kling-o3

> Curated from the fal.ai community team.

## What it does

Generate images and videos with Kling O3 — Kling's most 

### Lip Sync (`fal-lip-sync`)
---
name: fal-lip-sync
description: |
  Create talking head videos and lip sync audio to video via fal.ai. Useful for explainer avatars, multilingual dubbing previews, and social cuts.
triggers:
  - "lip sync"
  - "talking head"
  - "audio to video"
  - "avatar video"
  - "fal lipsync"
od:
  mode: video
  category: video-generation
  upstream: "https://github.com/fal-ai-community/skills"
---

# fal-lip-sync

> Curated from the fal.ai community te

### Media Studio (`fal-media-studio`)
---
name: fal-media-studio
description: Generate/edit images, video, audio and 3D via fal.ai with recipes for cinematic shots, character consistency/anime, storyboards, UGC, ads, upscaling. Use for any "generate image/video/3D/voice" request.
---

# fal-media-studio — one entry for fal.ai media work

Synthesis of two sources: **`fal-ai-community/skills`** (official community pack; CLI `genmedia`, endpoint-first routing, recipes) and **ECC `fal-ai

### Realtime (`fal-realtime`)
---
name: fal-realtime
description: |
  Real-time and streaming AI image generation via fal.ai. Suited for moodboard exploration, draft variations, and rapid creative iteration.
triggers:
  - "fal realtime"
  - "streaming image"
  - "realtime image gen"
  - "moodboard"
od:
  mode: image
  category: image-generation
  upstream: "https://github.com/fal-ai-community/skills"
---

# fal-realtime

> Curated from the fal.ai community team.

## What it d

### Restore (`fal-restore`)
---
name: fal-restore
description: |
  Restore and fix image quality — deblur, denoise, fix faces, and restore old documents using fal.ai's hosted restoration models.
triggers:
  - "fal restore"
  - "restore image"
  - "deblur"
  - "denoise"
  - "fix faces"
  - "document restore"
od:
  mode: image
  category: image-generation
  upstream: "https://github.com/fal-ai-community/skills"
---

# fal-restore

> Curated from the fal.ai community team.

##

### Train (`fal-train`)
---
name: fal-train
description: |
  Train custom AI models (LoRA) on fal.ai for personalized image generation tailored to a brand, character, or style.
triggers:
  - "fal train"
  - "train lora"
  - "custom model"
  - "personalized image gen"
  - "brand lora"
od:
  mode: image
  category: image-generation
  upstream: "https://github.com/fal-ai-community/skills"
---

# fal-train

> Curated from the fal.ai community team.

## What it does

Train c

### Tryon (`fal-tryon`)
---
name: fal-tryon
description: |
  Virtual try-on — see how clothes look on a person via fal.ai's hosted try-on models. Useful for ecommerce, lookbooks, and styling experiments.
triggers:
  - "virtual tryon"
  - "fal tryon"
  - "try on clothes"
  - "lookbook"
  - "ecommerce styling"
od:
  mode: image
  category: image-generation
  upstream: "https://github.com/fal-ai-community/skills"
---

# fal-tryon

> Curated from the fal.ai community team.


### Upscale (`fal-upscale`)
---
name: fal-upscale
description: |
  Upscale and enhance image and video resolution using AI super-resolution models hosted on fal.ai.
triggers:
  - "fal upscale"
  - "upscale image"
  - "super resolution"
  - "4k upscale"
  - "enhance resolution"
od:
  mode: image
  category: image-generation
  upstream: "https://github.com/fal-ai-community/skills"
---

# fal-upscale

> Curated from the fal.ai community team.

## What it does

Upscale and enha

### Video Edit (`fal-video-edit`)
---
name: fal-video-edit
description: |
  Edit existing videos using AI — remix style, upscale, remove background, and add audio via fal.ai's hosted video models.
triggers:
  - "fal video edit"
  - "video upscale"
  - "video style transfer"
  - "remove video bg"
  - "video remix"
od:
  mode: video
  category: video-generation
  upstream: "https://github.com/fal-ai-community/skills"
---

# fal-video-edit

> Curated from the fal.ai community team.


### Vision (`fal-vision`)
---
name: fal-vision
description: |
  Analyze images — segment objects, detect, run OCR, describe, and answer visual questions via fal.ai vision models.
triggers:
  - "fal vision"
  - "image analysis"
  - "object detection"
  - "ocr image"
  - "visual qa"
  - "segment"
od:
  mode: image
  category: image-generation
  upstream: "https://github.com/fal-ai-community/skills"
---

# fal-vision

> Curated from the fal.ai community team.

## What it doe

