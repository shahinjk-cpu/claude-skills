# Modelling the landmark (`P/landmark.py`)

The landmark is the only part made by hand. Everything about it comes from the photos and from published facts.

## Contract

```python
import bmesh, math
import pf_core as pf
import pf_look as look

KEEP_OUT = [(0.0, 0.0, 45.0)]      # discs (x, y, r) the generator leaves empty: the landmark's plot

def build(mp):                      # mp: the map (mp.in_water(x, y), mp.roads, mp.R, mp.free(x, y))
    ...
    return {"height": 351.5}

def update(frame, t):               # optional: called per film frame, t in seconds
    ...
```

Axes: metres, +X east, +Y north, +Z up, pin at the origin, ground at z = 0. A model drawn facing the camera can be
turned to true north at the end (see `TURN` in the Lotus example).

## Measure before modelling

1. Total height and part heights from published sources. Never from a guess.
2. On the target photo: rows of the base and of each break in the silhouette. With the base row `vb`, top row `vt`
   and height `H`, a row `v` is at height `H * (vb - v) / (vb - vt)` (a level, shifted camera keeps this linear).
3. Widths the same way: pixels x (H / (vb - vt)). A lathe profile `[(radius, z), ...]` falls straight out.
4. Proportions of the detailed parts from the **close-ups**, never the wide shot. Count repeated things (petals,
   columns, bays, floors) on the close-ups.

## Helpers (`engine/pf_core.py`)

| Call | Makes |
|---|---|
| `pf.lathe(bm, [(r, z), ...], seg=96, mat=0)` | Anything round: shafts, domes, drums. `seg=4` gives a square mast |
| `pf.extrude(bm, [(x, y), ...], z0, z1)` | Walls and slabs from a footprint |
| `pf.cube`, `pf.beam(bm, p1, p2, w)` | Blocks; struts, cables, railings |
| `pf.ribbon`, `pf.wall`, `pf.fill` | Paths, parapets, flat polygons (plazas, pools) |
| `pf.mesh_obj(name, bm, [mats], smooth=True)` | Finish a mesh as an object |
| `pf.simple_mat(name, colour, rough, metal, bump=)` | A constant Principled material (also right in the web viewer) |
| `look.mat_glass(name, colour, mullion)` | Curtain wall |
| `pf.new_mat` + `pf.nd / M / mix / ramp / noise_t ...` | Your own node shader (panel joints, cladding, LED lattices) |
| `pf.add_emission(mat, colour, strength)` | Night lighting. `pf.tod()` is `day`, `sunset` or `night` |
| `pf.time_value(nt, lambda t: ...)` | A value the film drives each frame (LED shows, beacons) |
| `pf.viewer_color(mat, colour, rough, metal)` | The average colour a node-driven material shows in the Three.js page |
| `pf.viewer_emission(mat, colour, strength)` | Its night glow in the Three.js page |

## Order of work (each step is a loop: `pf render P --view close`)

1. Big volumes and the silhouette. Check against the blend overlay before any detail.
2. The silhouette's corners: where shapes meet (collars, cornices, setbacks, the crown).
3. Materials: start with constant colours sampled from the photo in sunlight, then joints and panels.
4. Small parts: railings, antennas, plant rooms, the plinth and the plaza it stands on.
5. Night: a few emissive materials at low strength. Bright saturated emission turns white under AgX.

Rules that came from real mistakes:

- Outer layers must be outermost. Draw overlapping shells in the order they are seen.
- Faceted glass is flat-shaded panels with some metal, not a smooth mirror.
- Every part meets the ground or another part. Look from below and from above.
- Anything translucent used as a motion trick (rotor blur) must not cast a shadow.
- For recognisable objects on the plot (helicopter, statue, vehicles) find a CC0 or CC-BY model before modelling.
  `pf_life.load_model(path, name, collection, yaw, length=...)` imports a GLB in the engine's axes.
