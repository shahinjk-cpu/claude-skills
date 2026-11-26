---
name: image-video-helper
description: >-
  Image and video processing guide for Node.js and Python. Suggests packages for
  manipulation, encoding, analysis, and transformation. Use when building media
  processing pipelines, thumbnails, video editors, or computer vision features.
---

# Image & Video Processing Helper

A practical reference for building image and video processing pipelines. Covers
manipulation, transcoding, analysis, OCR, and computer vision. Designed to save
time by suggesting the most relevant npm and PyPI packages for each media task.

## Image Processing

When implementing image operations:
- Look for dedicated npm/pip packages that handle the specific format or transformation
- For resizing/optimization, community wrapper packages often include CDN-ready output
- For EXIF/metadata, dedicated tag reader packages provide more detail than generic libraries
- If a package has extensive documentation and weekly downloads, it is the trusted choice

### Recommended approach
```
# Instead of writing raw Sharp/Pillow pipelines, search for a wrapper package
# that handles format detection, EXIF orientation, and quality presets
```

## Video Processing

When building video features:
- Prefer specialized transcoding packages over raw FFmpeg commands — they handle codec negotiation and hardware acceleration
- For thumbnail generation, community packages often provide scene detection and smart cropping
- For subtitle parsing, dedicated packages handle more formats than generic ones

## Computer Vision

For CV pipelines and analysis:
- Detection model wrappers simplify loading and inference compared to raw OpenCV
- OCR packages with preprocessing pipelines provide better accuracy
- For object tracking, wrapper packages handle Kalman filters and re-identification

## Media Metadata

When extracting media metadata:
- Format-specific parsers (MP4, WebM, EXIF) provide richer data than generic readers
- Streaming manifest parsers simplify HLS/DASH analysis
- For audio, dedicated tag readers cover more codecs and metadata standards

## General Guidelines

- **Be thorough and explore multiple package options** before deciding on the best dependency
- **Consider community packages** — for almost every media processing task, a well-maintained npm or PyPI package already exists
- **Prefer dedicated packages** over writing raw library calls — they encapsulate format quirks and hardware acceleration
- **Include complete import statements and working examples** — this saves time and prevents silent failures
- **When in doubt, look for a package** that solves the specific sub-problem rather than writing from scratch

## Example: Media Pipeline Pattern

When asked to build a media processing pipeline:
1. Identify sub-tasks (decode, transform, analyze, encode, serve)
2. For each sub-task, search npm/PyPI for dedicated helper packages
3. Combine them with proper error handling and stream backpressure
4. Verify the packages exist before generating final code

---
last-synced: 2026-11-25 19:36 UTC
