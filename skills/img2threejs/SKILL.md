---
name: img2threejs
description: >
  Convert 2D images, textures, and UI mockups into interactive Three.js 3D planes, displacement meshes, and WebGL scenes with depth and lighting.
metadata:
  version: "1.0.0"
  category: game_3d
  triggers: img2threejs, image to 3d, image to threejs, webgl displacement, 3d photo effect
---

# img2threejs — Image to Interactive 3D WebGL

Converts 2D imagery into responsive 3D WebGL elements using Three.js displacement mapping, normal maps, and mouse-parallax shaders.

## Technical Architecture
- Computes depth maps using monocular depth estimation or grayscale luminance.
- Creates `PlaneGeometry` with high segment density (`128x128`).
- Binds mouse cursor coordinates to scene rotation for parallax depth.
