---
name: fal-ai-media-studio
description: >
  Master AI media generation suite powered by fal.ai APIs: text-to-image, Kling O3 video, inpainting, object removal, background removal, face restoration, upscale, 3D mesh sculpting, real-time generation, virtual try-on, and LoRA training.
category: ai_ml
version: "2.0.0"
role: consolidated_suite
triggers: fal-ai-media-studio, fal.ai generative media & vision studio, fal, fal-3d, fal-ai-media, fal-generate, fal-image-edit, fal-kling-o3, fal-lip-sync, fal-media-studio, fal-realtime, fal-restore, fal-train, fal-tryon, fal-upscale, fal-video-edit, fal-vision
---

# ✨ Fal.ai Generative Media & Vision Studio

Master AI media generation suite powered by fal.ai APIs: text-to-image, Kling O3 video, inpainting, object removal, background removal, face restoration, upscale, 3D mesh sculpting, real-time generation, virtual try-on, and LoRA training.

This is an **Automated Consolidated Modular Suite**. Rather than cluttering the catalog with dozens of separate micro-skills, this suite centralizes all related domain knowledge while keeping context and token costs minimal.

---

## 📚 Included Sub-Modules (14 Modules)

The following capabilities and domain modules are fully integrated into this suite:

- **`fal-3d`**: Generate 3D models from text or images via fal.ai. Useful for game assets, AR previews, product mockups, and concept sculpting.
  - *Reference File:* `references/fal-3d.md`
- **`fal-ai-media`**: Unified media generation via fal.ai MCP — image, video, and audio. Covers text-to-image (Nano Banana), text/image-to-video (Seedance, Kling, Veo 3), text-to-speech (CSM-1B), and video-to-audio (ThinkSound). Use when the user wants to generate images, videos, or audio with AI.
  - *Reference File:* `references/fal-ai-media.md`
- **`fal-generate`**: Generate images and videos using fal.ai AI models. Production-grade catalogue covering Flux, SDXL, ideogram, and other community-hosted endpoints.
  - *Reference File:* `references/fal-generate.md`
- **`fal-image-edit`**: AI-powered image editing with style transfer, background removal, object removal, and inpainting via fal.ai hosted models.
  - *Reference File:* `references/fal-image-edit.md`
- **`fal-kling-o3`**: Generate images and videos with Kling O3 — Kling's most powerful model family — via fal.ai.
  - *Reference File:* `references/fal-kling-o3.md`
- **`fal-lip-sync`**: Create talking head videos and lip sync audio to video via fal.ai. Useful for explainer avatars, multilingual dubbing previews, and social cuts.
  - *Reference File:* `references/fal-lip-sync.md`
- **`fal-media-studio`**: Generate/edit images, video, audio and 3D via fal.ai with recipes for cinematic shots, character consistency/anime, storyboards, UGC, ads, upscaling. Use for any "generate image/video/3D/voice" request.
  - *Reference File:* `references/fal-media-studio.md`
- **`fal-realtime`**: Real-time and streaming AI image generation via fal.ai. Suited for moodboard exploration, draft variations, and rapid creative iteration.
  - *Reference File:* `references/fal-realtime.md`
- **`fal-restore`**: Restore and fix image quality — deblur, denoise, fix faces, and restore old documents using fal.ai's hosted restoration models.
  - *Reference File:* `references/fal-restore.md`
- **`fal-train`**: Train custom AI models (LoRA) on fal.ai for personalized image generation tailored to a brand, character, or style.
  - *Reference File:* `references/fal-train.md`
- **`fal-tryon`**: Virtual try-on — see how clothes look on a person via fal.ai's hosted try-on models. Useful for ecommerce, lookbooks, and styling experiments.
  - *Reference File:* `references/fal-tryon.md`
- **`fal-upscale`**: Upscale and enhance image and video resolution using AI super-resolution models hosted on fal.ai.
  - *Reference File:* `references/fal-upscale.md`
- **`fal-video-edit`**: Edit existing videos using AI — remix style, upscale, remove background, and add audio via fal.ai's hosted video models.
  - *Reference File:* `references/fal-video-edit.md`
- **`fal-vision`**: Analyze images — segment objects, detect, run OCR, describe, and answer visual questions via fal.ai vision models.
  - *Reference File:* `references/fal-vision.md`

---

## 🎯 How the Agent Uses This Suite

1. **Selective Context Loading (Token Economical)**:
   - When a specific sub-task is requested (e.g. `fal-3d`), do NOT read the entire suite.
   - Use `read_file` to inspect only the required reference document under `references/<submodule>.md`.

2. **Cross-Module Synergy**:
   - If a project requires multiple aspects (e.g., both 2D movement and physics, or both SQLi and XSS testing), the agent can consult the corresponding reference files seamlessly without losing context or requiring separate skill invocations.
