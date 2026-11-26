"""The landmark: the one thing in the scene that is modelled by hand, from the reference photos.

`pf init` copies this file to <project>/landmark.py. Replace build() with the real landmark. Until you do, the
map's own footprint stands in (delete this file, or leave build() returning None, to keep the mapped building).

Axes: metres, +X east, +Y north, +Z up, the map pin at (0, 0, 0), ground at z = 0.
Helpers (import pf_core as pf, pf_look as look):
    pf.lathe(bm, [(radius, z), ...])       towers, domes, columns, anything round
    pf.extrude(bm, [(x, y), ...], z0, z1)  walls and slabs from a footprint
    pf.cube / pf.beam / pf.ribbon / pf.wall / pf.fill
    pf.mesh_obj(name, bm, [materials], smooth=True)
    pf.simple_mat(name, colour, rough, metal)      constant Principled: also shows correctly in the web viewer
    look.mat_glass(name, colour, mullion)          curtain wall
    pf.add_emission(mat, colour, strength)         night lighting;  pf.tod() is "day" | "sunset" | "night"
    pf.time_value(node_tree, lambda t: ...)        a value the film drives every frame (LED shows, beacons)

How to get it right (the order matters):
    1. Facts first: total height and the height of each part (Wikipedia, Structurae, the architect's drawings).
    2. Proportions from the close-up photos, not the wide one: measure widths against the known height in pixels.
    3. Big shapes, then the silhouette's corners, then materials, then small parts. Render view=close each loop.
    4. Outer layers outermost; nothing floating; every part meets the ground or another part.
"""
import bmesh, math
import pf_core as pf
import pf_look as look

# Discs (x, y, radius) the generator must leave empty: the landmark's own plot. Mapped buildings whose centre falls
# inside, trees and generated lots are removed; streets stay.
KEEP_OUT = []          # e.g. [(0.0, 0.0, 45.0)]


def build(mp):
    """Build the landmark at the origin. mp is the map (mp.in_water(x, y), mp.roads, mp.R ...).
    Return {"height": metres} so cameras and film shots frame it."""
    return None

    # --- a worked sketch: a round concrete tower with a glazed pod and a mast (delete `return None` above to see it)
    concrete = pf.simple_mat("lm_concrete", (0.55, 0.54, 0.50), 0.8, bump=0.1)
    glass = look.mat_glass("lm_glass", (0.08, 0.12, 0.15), mullion=2.4)
    steel = pf.simple_mat("lm_steel", (0.6, 0.6, 0.62), 0.35, 0.9)
    bm = bmesh.new()
    pf.lathe(bm, [(9.0, 0.0), (7.5, 20.0), (6.0, 120.0), (6.0, 150.0)], mat=0)                      # shaft
    pf.lathe(bm, [(6.0, 150.0), (14.0, 156.0), (15.0, 166.0), (11.0, 174.0)], mat=1, cap_top=True)   # pod
    pf.lathe(bm, [(1.2, 174.0), (0.4, 220.0)], seg=12, mat=2, cap_top=True)                          # mast
    pf.mesh_obj("landmark", bm, [concrete, glass, steel], smooth=True)
    if pf.tod() == "night":
        pf.add_emission(glass, (1.0, 0.8, 0.5), 1.2)
    return {"height": 220.0}


def update(frame, t):
    """Optional: called for every film frame with the time in seconds (turn a rotor, move a lift, swap a colour)."""
    pass
