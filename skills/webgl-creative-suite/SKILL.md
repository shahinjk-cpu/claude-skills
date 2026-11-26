---
name: webgl-creative-suite
description: Creative WebGL and Three.js master shader effects library (aurora veils, caustic pools, depth galleries, particle galaxies, liquid metals, voronoi noise, post-processing).
---

# WebGL Creative Shaders & Visual Effects Master Suite

High-performance GLSL shaders, Three.js scenes, and fluid GPU visual effects for immersive web experiences.

## Shader Effects Catalog
### Aurora Veil (`webgl-aurora-veil`)
---
name: webgl-aurora-veil
description: |
  A self-contained WebGL2 hero: layered aurora light curtains warped over a night sky scattered with stars; move the cursor to sway the veil.
triggers:
  - "aurora veil"
  - "webgl hero"
od:
  mode: prototype
  platform: web
  scenario: design
  preview:
    type: html
    entry: index.html
    reload: debounce-100
  design_system:
    requires: false
  craft:
    requires: [animation-discipline]
---

# 

### Caustic Pool (`webgl-caustic-pool`)
---
name: webgl-caustic-pool
description: |
  A self-contained WebGL2 hero: animated water caustics woven from domain-warped ripples; click the water to drop a ripple. No meshes, no textures.
triggers:
  - "caustic pool"
  - "webgl hero"
od:
  mode: prototype
  platform: web
  scenario: design
  preview:
    type: html
    entry: index.html
    reload: debounce-100
  design_system:
    requires: false
  craft:
    requires: [animation-discipline]

### Depth Gallery (`webgl-depth-gallery`)
---
name: webgl-depth-gallery
description: |
  A scroll-reactive 3D image gallery in Three.js: Z-stacked images crossfade over per-image mood backgrounds with velocity breath, a glowing cursor trail and an editorial CMYK/RGB/HEX/PMS color card.
triggers:
  - "depth gallery"
  - "webgl gallery"
od:
  mode: prototype
  platform: web
  scenario: design
  preview:
    type: html
    entry: index.html
    reload: debounce-100
  design_system:
    requ

### Distortion Grain (`webgl-distortion-grain`)
---
name: webgl-distortion-grain
description: |
  A vertical gallery (Three.js) where planes bend with scroll velocity, ripple under the cursor via simplex noise, and carry a film grain.
triggers:
  - "distortion & grain"
  - "webgl gallery"
od:
  mode: prototype
  platform: web
  scenario: design
  preview:
    type: html
    entry: index.html
    reload: debounce-100
  design_system:
    requires: false
  craft:
    requires: [animation-discipl

### Experience (`webgl-experience`)
---
name: webgl-experience
description: |
  A full-screen, real-time WebGL/WebGL2 experience — animated shaders, 3D
  scenes, generative visuals, particle fields — rendered live on the GPU with
  a typographic overlay. Produced as a single self-contained `index.html`.
  Use when the brief asks for a "WebGL", "shader", "3D", "generative", "GPU",
  "interactive canvas", "hero animation", or "real-time visual" experience.
  OpenDesign serves this in

### Halftone Drift (`webgl-halftone-drift`)
---
name: webgl-halftone-drift
description: |
  A self-contained WebGL2 hero: a flowing field screened through a rotated halftone dot grid into a duotone print aesthetic; move the cursor to bend the drift.
triggers:
  - "halftone drift"
  - "webgl hero"
od:
  mode: prototype
  platform: web
  scenario: design
  preview:
    type: html
    entry: index.html
    reload: debounce-100
  design_system:
    requires: false
  craft:
    requires: [anima

### Holographic Foil (`webgl-holographic-foil`)
---
name: webgl-holographic-foil
description: |
  A self-contained WebGL2 hero: thin-film interference over a crushed-foil surface whose palette shifts with the viewing angle; move the cursor to tilt the film.
triggers:
  - "holographic foil"
  - "webgl hero"
od:
  mode: prototype
  platform: web
  scenario: design
  preview:
    type: html
    entry: index.html
    reload: debounce-100
  design_system:
    requires: false
  craft:
    requires: 

### Horizontal Parallax (`webgl-horizontal-parallax`)
---
name: webgl-horizontal-parallax
description: |
  A horizontal-scroll WebGL gallery (Three.js): frames glide sideways with lerp smoothing and each image parallaxes its texture (UV shift) by its position in the viewport.
triggers:
  - "horizontal parallax gallery"
  - "webgl gallery"
od:
  mode: prototype
  platform: web
  scenario: design
  preview:
    type: html
    entry: index.html
    reload: debounce-100
  design_system:
    requires: fa

### Liquid Iridescence (`webgl-liquid-iridescence`)
---
name: webgl-liquid-iridescence
description: |
  A self-contained WebGL2 hero: a living oil-on-water field brightened into iridescent caustic filaments; move the cursor to bend the flow.
triggers:
  - "liquid iridescence"
  - "webgl hero"
od:
  mode: prototype
  platform: web
  scenario: design
  preview:
    type: html
    entry: index.html
    reload: debounce-100
  design_system:
    requires: false
  craft:
    requires: [animation-discipl

### Liquid Metal (`webgl-liquid-metal`)
---
name: webgl-liquid-metal
description: |
  A real-time liquid-metal shader — a domain-warped noise field shaded as
  molten chrome, with a sweeping specular highlight over an iridescent
  thin-film (cosine-palette) sheen. No textures. Rendered as a single
  self-contained `index.html`. Use when the brief asks for "liquid metal",
  "molten chrome", "iridescent", "holographic", "metallic", "thin-film", or a
  reflective flowing surface. OpenDesi

### Neon Grid (`webgl-neon-grid`)
---
name: webgl-neon-grid
description: |
  A real-time synthwave scene — a perspective floor grid scrolling toward a
  banded retro sun under a neon starfield, all from one fragment shader. No
  textures. Rendered as a single self-contained `index.html`. Use when the
  brief asks for "synthwave", "outrun", "retro 80s", "neon grid", "perspective
  grid", "vaporwave", or a retro-futuristic hero. OpenDesign serves this in
  powered-preview mode so t

### Particle Galaxy (`webgl-particle-galaxy`)
---
name: webgl-particle-galaxy
description: |
  A real-time particle galaxy — tens of thousands of additive-blended GPU
  points spiraling around a bright core, their orbits solved entirely in the
  vertex shader (from gl_VertexID), so the whole cloud draws in one call.
  Rendered as a single self-contained `index.html`. Use when the brief asks
  for a "particle field", "particle galaxy", "point cloud", "instanced
  points", "starfield", "GPU pa

### Pixel Reveal Gallery (`webgl-pixel-reveal-gallery`)
---
name: webgl-pixel-reveal-gallery
description: |
  A scroll-reactive masonry gallery (Three.js + GSAP) where each image develops from a pixel/grid dissolve on viewport entry, with a split-text heading and click-to-fullscreen Flip.
triggers:
  - "pixel reveal gallery"
  - "webgl gallery"
od:
  mode: prototype
  platform: web
  scenario: design
  preview:
    type: html
    entry: index.html
    reload: debounce-100
  design_system:
    requires

### Raymarched Hero (`webgl-raymarched-hero`)
---
name: webgl-raymarched-hero
description: |
  A real-time raymarched 3D hero — soft-shadowed morphing metaballs with a
  fresnel rim light, sphere-traced per pixel in a fragment shader with a slow
  camera orbit. No meshes, no textures. Rendered as a single self-contained
  `index.html`. Use when the brief asks for a "raymarch", "signed distance
  field", "SDF", "3D hero", "metaballs", "blobs", or a shader-based 3D scene.
  OpenDesign serves t

### Voronoi Cells (`webgl-voronoi-cells`)
---
name: webgl-voronoi-cells
description: |
  A self-contained WebGL2 hero: a living Voronoi network with drifting feature points, palette-keyed cells and glowing boundaries; move the cursor to push the cells.
triggers:
  - "voronoi cells"
  - "webgl hero"
od:
  mode: prototype
  platform: web
  scenario: design
  preview:
    type: html
    entry: index.html
    reload: debounce-100
  design_system:
    requires: false
  craft:
    requires: [a

