# Blender 5.3 VSE — API notes for scripted edits

Verified on Blender 5.3.0 (Steam). Helpers live in `<VSEKIT>/vsekit/vse.py`, `fx.py`, `three_d.py`.

## Contents
1. Coordinates & placement
2. Strips
3. Keyframes & easing
4. Meta, effects, adjustment layers
5. Compositor modifiers (node-group FX)
6. Retiming (speed ramps)
7. Audio
8. Scene strips (3D)
9. Rendering & OTIO
10. Driving the user's open Blender (MCP)

## 1. Coordinates & placement
- `strip.transform.offset_x/offset_y` are pixels; y points **up**; image centre sits at canvas centre.
  `vse.place(strip, x, y)` takes top-left-origin canvas pixels.
- `transform.origin` is normalised (0..1), y from the **bottom**. Scaling text strips happens around the
  canvas, so set `origin = (x/W, 1 - y/H)` to scale around the text itself.
- `crop.min_x` etc. crop in pixels without moving the image (used for before/after sliders).

## 2. Strips
- `ed = scene.sequence_editor_create()`; collections are `ed.strips` / `ed.strips_all` (old `sequences*` gone).
- `ed.strips.new_image(name, path, ch, start, fit_method='ORIGINAL'|'FIT'|'FILL'|'STRETCH')`.
- `ed.strips.new_movie(..., fit_method='FIT')` — **pass it**: from scripts the default is original size, so a
  720p clip sits small in a 1080p frame (seen in the jump-cut demo). There is no `strip.fit_method` property.
- Image sequences: create with the first file, then `strip.elements.append(basename)` for the rest.
- Trimming a source range `[a,b]` to timeline frame `t`: create at `t - a*fps`, then set
  `frame_final_start = t`, `frame_final_end = t + (b-a)*fps` (`vse.clip()`). These props warn
  "removed in 6.0" — newer names exist (`left_handle`/`right_handle`), migrate when 6.0 lands.
- Text strip: `new_effect(name,'TEXT',channel,frame_start,length)`; props `text, font (bpy.data.fonts.load),
  font_size (px), color, location (0..1, y up), anchor_x/anchor_y, alignment_x, use_box, box_color,
  box_margin (small! 0.004–0.012), box_roundness, use_outline, outline_width, use_shadow, wrap_width`.
  One colour per strip — multi-colour/word-highlight captions are baked with Pillow instead.
- Channel names: `ed.channels[i].name = "Captions"`.
- `blend_type='ALPHA_OVER'` on overlays; `blend_alpha` is the animatable opacity.

## 3. Keyframes & easing
- `obj.keyframe_insert(prop, frame=f)` works on strips, `strip.transform`, `strip.crop`, node sockets
  (`default_value`) and objects. Animation lives on the owning ID (scene for strips, node tree for sockets).
- Blender 5 actions are layered: get F-curves via
  `bpy_extras.anim_utils.action_get_channelbag_for_slot(ad.action, ad.action_slot).fcurves`.
- Interpolation is set on the key that **starts** a segment: `kp.interpolation = 'BACK'|'EXPO'|'CUBIC'|...`,
  `kp.easing = 'EASE_OUT'`. `vse.key()` does this.
- Camera shake = F-curve `NOISE` modifier with restricted range + blend out (`vse.shake()`), usually on an
  adjustment strip so it shakes everything below.

## 4. Meta, effects, adjustment layers
- `m = ed.strips.new_meta(name, ch, start)`; `s.move_to_meta(m)`; then **set `m.frame_final_end`** — the
  meta stays 1 frame long otherwise and renders nothing.
- Moving an input strip into a meta moves its effect strips too; moving the effect again raises
  "already inside" → check `s.parent_meta() != m` first.
- Effects: `CROSS, ADD, WIPE, GLOW, GAUSSIAN_BLUR (size_x/size_y), COLOR, SPEED, ADJUSTMENT, TEXT,
  COMPOSITOR (5.3), COLORMIX, MULTICAM`. `new_effect(..., input1=, input2=)`.
- Adjustment strips apply their transform + modifiers to everything in lower channels → use for punch-ins,
  shake, whips, glitches, and the global grade (put captions/progress bar above if they must stay still).

## 5. Compositor modifiers (node-group FX)
- `m = strip.modifiers.new(name, 'COMPOSITOR'); m.node_group = ng` where `ng` is a `CompositorNodeTree`
  with interface sockets `Image` in/out (`fx.new_group`). Other modifier types: BRIGHT_CONTRAST,
  COLOR_BALANCE, CURVES, HUE_CORRECT, MASK, TONEMAP, WHITE_BALANCE, SOUND_EQUALIZER, PITCH, ECHO.
- Many node options are now **MENU sockets** set by display name: Glare `Type='Bloom'`, Translate
  `Extension X='Repeat'`, EllipseMask `Operation='Add'`, Blur `Type='Gaussian'`.
- Available and useful: Glare, Lensdist (dispersion = chromatic aberration), DBlur (Amount, Direction),
  EllipseMask/BoxMask, Translate, Transform, SeparateColor/CombineColor, Pixelate, HueSat, ColorBalance,
  Blur (Size vector px), `ShaderNodeMix` (RGBA, blend modes), `ShaderNodeMath`, `ShaderNodeTexNoise`
  (grain), `CompositorNodeImageCoordinates`, `CompositorNodeSceneTime` (frame for animated grain).
  `CompositorNodeMixRGB/Math/Vignette` no longer exist.
- `scene.render.compositor_device = 'GPU'` speeds this up.

## 6. Retiming (speed ramps)
- `k = strip.retiming_keys.add(timeline_frame=F)`; keys only expose `timeline_frame`.
- Moving a key changes the speed of the segment before it **and does not shift later keys**; adjust the
  last key too (e.g. to the section end) or the tail plays fast. Works on movie and scene strips.

## 7. Audio
- Sound strips: `new_sound`; `volume` animatable (ducking under VO, 2-frame fades at jump cuts to avoid clicks).
- The mix is summed: VO + music + SFX clipped at +2.4 dBTP once. Set `scene.audio_volume = 0.6`, then
  `media.finalize()` (ffmpeg loudnorm −14 LUFS / −1.5 dBTP).
- Blender reads mp3 directly, but convert TTS to 48 kHz wav for exact durations.

## 8. Scene strips (3D)
- `ed.strips.new_scene(name, scene, ch, start)`; the 3D scene renders with EEVEE (`BLENDER_EEVEE`) at its own
  resolution — set it equal to the edit scene. Motion blur: `scene.render.use_motion_blur`.
- Voxel models from `ArtSources/Blender/*.blend` hold one mesh per pose (`*_Idle`, `*_Walk_00..03`) →
  stop-motion by keying `hide_render/hide_viewport` with CONSTANT interpolation (`three_d.stop_motion`).
- Particles with negative `frame_start` pre-roll fine in background renders.

## 9. Rendering & OTIO
- `scene.render.image_settings.media_type = 'VIDEO'` before `file_format='FFMPEG'`; for stills use
  `media_type='IMAGE'`, `file_format='PNG'`. `use_file_extension=False` to keep the exact filename.
- Render in a separate process: `blender -b file.blend -a` (run in background; 35 s 1080×1920 ≈ 2 min).
- OTIO: `bpy.ops.wm.otio_export(filepath=...)` / `otio_import`. In `-b` mode it fails with "No sequencer
  scene" unless `ws = bpy.data.workspaces[0]; ws.sequencer_scene = scn` and
  `with bpy.context.temp_override(workspace=ws, scene=scn): ...`. DaVinci Resolve imports `.otio` directly.
- `scene.view_settings.view_transform = 'Standard'` for the edit scene (AgX desaturates screenshots).

## 10. Driving the user's open Blender (MCP)
- `execute_blender_code` runs in the UI session; return a dict in `result`.
- Before opening/reloading another file check `bpy.data.is_dirty`; if dirty, ask.
- Long renders block the UI — use a background process instead and `open_mainfile` only when the user agrees.
