"""Generate millimetre calibration solids for the War Thunder miniature pipeline.

Run with FreeCAD's bundled Python. The geometry needs FreeCAD, Part and
MeshPart; matplotlib is only used for the optional preview.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import FreeCAD as App
import Part
import MeshPart


PIN_DIAMETER_MM = 5.0
ENGAGEMENT_MM = 3.0
BORE_DEPTH_MM = 3.4
CLEARANCES_MM = (0.15, 0.20, 0.25)
SOCKET_CENTER = (9.0, 9.0)
SOCKET_TOP_MM = 5.0


def box(dx, dy, dz, x=0.0, y=0.0, z=0.0):
    return Part.makeBox(dx, dy, dz, App.Vector(x, y, z))


def fuse(shapes):
    result = shapes[0]
    if len(shapes) > 1:
        result = result.multiFuse(shapes[1:])
    return result.removeSplitter()


def raised_number(text, x, y, z, height=0.4):
    """Font-independent, 0.4 mm stroke seven-segment labels."""
    segments = {
        "a": (0.0, 2.4, 1.6, 0.4),
        "b": (1.2, 1.2, 0.4, 1.6),
        "c": (1.2, 0.0, 0.4, 1.6),
        "d": (0.0, 0.0, 1.6, 0.4),
        "e": (0.0, 0.0, 0.4, 1.6),
        "f": (0.0, 1.2, 0.4, 1.6),
        "g": (0.0, 1.2, 1.6, 0.4),
    }
    digits = {
        "0": "abcdef", "1": "bc", "2": "abged", "3": "abgcd",
        "4": "fgbc", "5": "afgcd", "6": "afgecd", "7": "abc",
        "8": "abcdefg", "9": "abfgcd",
    }
    solids = []
    cursor = x
    for char in text:
        if char == ".":
            solids.append(box(0.4, 0.4, height + 0.02, cursor, y, z - 0.02))
            cursor += 0.8
            continue
        for key in digits[char]:
            sx, sy, dx, dy = segments[key]
            solids.append(box(dx, dy, height + 0.02, cursor + sx, y + sy, z - 0.02))
        cursor += 2.0
    return solids


def make_pin():
    # Flat flange printed on the bed; straight working section plus lead-in.
    flange = Part.makeCylinder(4.0, 2.0)
    stem = Part.makeCylinder(PIN_DIAMETER_MM / 2, ENGAGEMENT_MM - 0.25,
                             App.Vector(0, 0, 2.0))
    lead_in = Part.makeCone(2.5, 2.25, 0.25, App.Vector(0, 0, 4.75))
    return fuse([flange, stem, lead_in])


def make_socket(radial_clearance):
    slab = box(18.0, 14.0, SOCKET_TOP_MM)
    radius = PIN_DIAMETER_MM / 2 + radial_clearance
    bore = Part.makeCylinder(radius, BORE_DEPTH_MM + 0.1,
                             App.Vector(*SOCKET_CENTER, SOCKET_TOP_MM - BORE_DEPTH_MM))
    result = slab.cut(bore)
    # Label is outside the pin flange contact area.
    return fuse([result] + raised_number(f"{radial_clearance:.2f}", 5.8, 0.7, SOCKET_TOP_MM))


def make_detail_sample():
    floor = 1.6
    pieces = [box(50.0, 32.0, floor)]
    # Unsupported vertical rods: compare 0.6, 0.8, 1.0 mm at identical height.
    for x, diameter in zip((5.0, 11.0, 17.0), (0.6, 0.8, 1.0)):
        pieces.append(Part.makeCylinder(diameter / 2, 6.02,
                                       App.Vector(x, 9.0, floor - 0.02)))
        pieces.extend(raised_number(f"{diameter:.1f}", x - 2.8, 2.0, floor))
    # Thin walls, all 15 mm long and 5 mm tall.
    for y, thickness, label in ((19.0, 0.6, "6"), (23.0, 0.8, "8"), (27.0, 1.0, "10")):
        pieces.append(box(15.0, thickness, 5.02, 3.0, y, floor - 0.02))
        pieces.extend(raised_number(label, 20.0, y - 0.8, floor))
    # A miniature protective grille: 0.8 mm rails and posts, 3.5 mm openings.
    grille_x, grille_y, grille_h, grille_w, t = 28.0, 8.0, 8.0, 18.0, 0.8
    pieces.append(box(grille_w, t, t + 0.02, grille_x, grille_y, floor - 0.02))
    pieces.append(box(grille_w, t, t, grille_x, grille_y, floor + grille_h - t))
    for x in (28.0, 32.3, 36.6, 40.9, 45.2):
        pieces.append(box(t, t, grille_h + 0.02, x, grille_y, floor - 0.02))
    pieces.extend(raised_number("0.8", 34.0, 2.0, floor))
    return fuse(pieces)


def inspect_shape(shape):
    if not shape.isValid() or len(shape.Solids) != 1:
        raise RuntimeError("Calibration part must be one valid connected solid")
    mesh = MeshPart.meshFromShape(Shape=shape, LinearDeflection=0.01,
                                  AngularDeflection=0.05, Relative=False)
    if not mesh.isSolid() or mesh.hasNonManifolds():
        raise RuntimeError("Calibration mesh is not closed/manifold")
    bounds = shape.BoundBox
    return mesh, {
        "units": "mm", "cad_valid": shape.isValid(), "solid_count": len(shape.Solids),
        "mesh_closed": mesh.isSolid(), "mesh_non_manifold": mesh.hasNonManifolds(),
        "triangles": mesh.CountFacets, "volume_mm3": shape.Volume,
        "size_mm": [bounds.XLength, bounds.YLength, bounds.ZLength],
        "z_min_mm": bounds.ZMin,
    }


def make_preview(parts, destination):
    # Keep font/cache writes within the generated artifact directory.
    mpl_cache = Path(destination).parent / ".mplconfig"
    mpl_cache.mkdir(parents=True, exist_ok=True)
    os.environ["MPLCONFIGDIR"] = str(mpl_cache)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    import numpy as np

    fig = plt.figure(figsize=(12, 7), facecolor="#f8fafc")
    ax = fig.add_subplot(111, projection="3d")
    ax.set_facecolor("#f8fafc")
    layout = [(0, 0), (14, 0), (36, 0), (58, 0), (15, 25)]
    colors = ["#f59e0b", "#38bdf8", "#22c55e", "#8b5cf6", "#94a3b8"]
    for (name, (_, mesh)), (dx, dy), color in zip(parts.items(), layout, colors):
        points, faces = mesh.Topology
        vertices = np.array([[p.x + dx, p.y + dy, p.z] for p in points])
        poly = Poly3DCollection(vertices[np.array(faces)], facecolors=color,
                               edgecolor="none", shade=True,
                               lightsource=matplotlib.colors.LightSource(315, 45))
        ax.add_collection3d(poly)
    ax.set(xlim=(-8, 82), ylim=(-8, 65), zlim=(0, 20))
    ax.set_box_aspect((90, 73, 20))
    ax.view_init(elev=37, azim=-57)
    ax.set_xlabel("mm")
    ax.set_ylabel("mm")
    ax.set_zlabel("mm")
    ax.set_title("A1 mini · 0.2 mm nozzle · PLA\nPin Ø5 / radial clearances 0.15 · 0.20 · 0.25 mm / detail sample", pad=15)
    fig.text(0.5, 0.03, "Digital geometry verified. Physical fit and detail survival need a test print.",
             ha="center", color="#334155")
    fig.savefig(destination, dpi=150, bbox_inches="tight")
    plt.close(fig)


def generate(output_dir, preview=True):
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    shapes = {"turret_pin_5mm": make_pin()}
    for clearance in CLEARANCES_MM:
        shapes[f"turret_socket_clearance_{clearance:.2f}".replace(".", "p")] = make_socket(clearance)
    shapes["detail_sample_0p6_0p8_1p0"] = make_detail_sample()
    doc = App.newDocument("WarThunderCalibration")
    report = {
        "generator": "make_calibration.py", "units": "mm", "physical_test_passed": False,
        "pin_diameter_mm": PIN_DIAMETER_MM, "engagement_mm": ENGAGEMENT_MM,
        "bore_depth_mm": BORE_DEPTH_MM, "clearance_convention": "radial, per side",
        "radial_clearances_mm": list(CLEARANCES_MM),
        "bore_diameters_mm": [PIN_DIAMETER_MM + 2 * c for c in CLEARANCES_MM],
        "printer": "Bambu Lab A1 mini", "nozzle_mm": 0.2, "material": "PLA",
        "layer_height_mm": 0.08, "parts": [],
    }
    parts = {}
    for name, shape in shapes.items():
        mesh, checks = inspect_shape(shape)
        mesh.write(str(output_dir / f"{name}.stl"))
        obj = doc.addObject("PartDesign::Feature", name.replace(".", "_"))
        obj.Label = name
        obj.Shape = shape
        checks.update({"name": name, "stl": f"{name}.stl"})
        report["parts"].append(checks)
        parts[name] = (shape, mesh)
    doc.recompute()
    doc.saveAs(str(output_dir / "calibration.FCStd"))
    App.closeDocument(doc.Name)
    (output_dir / "calibration_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (output_dir / "README.txt").write_text(
        "WAR THUNDER CALIBRATION - PLA / A1 mini / 0.2 mm nozzle / 0.08 mm layers\n"
        "All STL files use millimetres. Print original orientation, 100% scale.\n"
        "Socket labels are RADIAL clearance per side: 0.15 / 0.20 / 0.25 mm.\n"
        "Bores: 5.30 / 5.40 / 5.50 mm. Pin: 5.00 mm; engagement 3.00 mm.\n"
        "Bore depth 3.40 mm avoids bottoming. Pin lead-in: 0.25 mm.\n"
        "Print pin separately, flat flange on bed, shaft up. Sockets: holes up.\n"
        "Turn pin shaft down for insertion. Choose smallest clearance rotating freely\n"
        "without forcing. Record result before manufacturing final turret joint.\n"
        "A socket label must not be used as the contact face for pin flange.\n"
        "Detail sample: rods (6 mm tall) 0.6/0.8/1.0 mm diameter; walls (5 mm tall)\n"
        "0.6/0.8/1.0 mm thick, labeled 6/8/10; grille members 0.8 mm.\n"
        "Labels have 0.4 mm strokes and 0.4 mm relief. They are cosmetic.\n"
        "Use no supports for these coupons; inspect bridge quality on grille.\n"
        "Match filament and slicing profile to final miniature. Physical tests pending.\n",
        encoding="utf-8")
    if preview:
        make_preview(parts, output_dir / "calibration_preview.png")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path,
                        default=Path(__file__).resolve().parents[1] / "calibration")
    parser.add_argument("--no-preview", action="store_true")
    args = parser.parse_args()
    report = generate(args.output_dir, not args.no_preview)
    print(json.dumps({"output_dir": str(args.output_dir.resolve()), "parts": len(report["parts"]),
                      "all_valid": True, "physical_test_passed": False}))


if __name__ == "__main__":
    main()
