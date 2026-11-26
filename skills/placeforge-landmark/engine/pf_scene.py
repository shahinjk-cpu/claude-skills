"""placeforge engine, entry point. Builds the place and renders, exports or films it.

    blender -b --python pf_scene.py -- project=<dir> [key=value ...]

    build=1                 build only, render nothing (checks the scripts; fine on any machine)
    view=<name>             photo | hero | wide | close | top | street | any view in place.json
    name=<file>             output name in <project>/renders/ (default: the view's name)
    pct=50 samples=64       preview size and quality;  w= h=  the frame
    tod=day|sunset|night    time of day
    fmt=jpg                 write a JPEG instead of a PNG (small previews to pull from a rented machine)
    anim=1 frames=a-b       film frames from film/shots.json into <project>/film/frames/
    anim=1 pick=12,200      single film frames as stills (look-dev of the shots)
    export=web              scene.bin + scene.json for the Three.js viewer in <project>/web/data/
    save=<file.blend>       keep the built scene
    device=CPU|CUDA|OPTIX|HIP|ONEAPI|METAL     force a render device
    look.exposure.day=0.6   any dotted key overrides place.json for this run (how the loop tunes)
"""
import bpy, importlib.util, math, os, random, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pf_core as pf
import pf_look as look
import pf_city as city
import pf_cam as cam
from pf_core import arg, cfg


def load_landmark():
    p = os.path.join(pf.PROJECT, cfg("landmark.script", "landmark.py"))
    if not os.path.exists(p):
        pf.log("no landmark.py: the map's own footprint stands in for the landmark")
        return None
    spec = importlib.util.spec_from_file_location("landmark", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def render_still(sc, name):
    out = os.path.join(pf.PROJECT, "renders")
    os.makedirs(out, exist_ok=True)
    jpg = arg("fmt") == "jpg"
    sc.render.image_settings.file_format = "JPEG" if jpg else "PNG"
    if jpg:
        sc.render.image_settings.quality = 92
    else:
        sc.render.image_settings.color_depth = "8"
    sc.render.filepath = os.path.join(out, name + (".jpg" if jpg else ".png"))
    bpy.ops.render.render(write_still=True)
    pf.log("SAVED", sc.render.filepath)


def main():
    t0 = time.time()
    if not arg("project"):
        raise SystemExit(__doc__)
    pf.init(arg("project"))
    anim = arg("anim") == "1"
    shots = fps = None
    if anim:
        shots, fps = cam.load_shots()
        f0 = int((arg("frames") or arg("pick", "1")).replace("-", ",").split(",")[0])
        pf.ARGS["tod"] = next((s.get("tod", "day") for s in shots if s["a"] <= f0 <= s["b"]), "day")
    pf.log("place:", cfg("name"), "| time of day:", pf.tod())
    sc = look.scene()
    look.world(sc)
    look.sun_lamp()
    lm = load_landmark()
    mp, B, trees = city.build(int(arg("seed", 1)), getattr(lm, "KEEP_OUT", ()))
    H = float(cfg("landmark.height_m", 0) or 0)
    if lm:
        info = lm.build(mp) or {}
        H = float(info.get("height", H) or H)
    if H <= 0:                                    # no model, no stated height: the tallest mapped thing at the pin
        H = max([b.get("h", 0) or 0 for b in mp.buildings if city.inside(b["p"], 0.0, 0.0)] + [30.0])
    rng = random.Random(7)
    trees = city.finish(mp, B, trees, rng)
    reach = max(mp.FR * 4.0, 25000.0)
    look.haze(reach)
    look.clouds(reach)
    if arg("grade", "1") == "1":
        look.grade(sc)
    life = None
    if arg("life", "1") == "1":
        try:
            import pf_life
            life = pf_life.build(mp, rng, H)
        except Exception as e:
            pf.log("life skipped:", repr(e))
    pf.log("built in %.1f s" % (time.time() - t0))
    if arg("export") == "web":
        import pf_export
        pf_export.export(mp, B, trees, H, life)
        return
    c = cam.camera(sc, mp, H) if not anim else None
    poses = None
    if anim:
        c = bpy.data.cameras.new("cam")
        c.sensor_width, c.clip_start, c.clip_end = 36.0, 0.5, 200000
        o = pf.link_obj(bpy.data.objects.new("cam", c))
        sc.camera = o
        poses = cam.animate(sc, o, shots, fps)
        c = o

    def update(f):
        """Everything that moves, placed for frame f (frames render one at a time, in any order, on any machine)."""
        t = (f - 1) / float(fps or 24)
        if poses:
            cam.set_frame(c, poses, f)
        for sock, fn in pf.TIMED:
            sock.default_value = fn(t)
        if life:
            life.update(f, t)
        if lm and hasattr(lm, "update"):
            lm.update(f, t)

    if arg("save"):
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(arg("save")))
        pf.log("SAVED", arg("save"))
    if arg("build") == "1":
        if anim:
            for s in shots:
                update(s["a"])
                update(s["b"])
            pf.log("film: %d shots, %d frames, %.1f s at %d fps: per-frame update ok" % (len(shots), shots[-1]["b"], shots[-1]["b"] / fps, fps))
        pf.log("BUILD OK")
        return
    if anim:
        if arg("frames"):
            a, b = (int(x) for x in arg("frames").split("-"))
            out = os.path.join(pf.PROJECT, "film", "frames")
            os.makedirs(out, exist_ok=True)
            sc.render.image_settings.file_format = "PNG"
            sc.render.image_settings.color_depth = "8"
            sc.render.use_persistent_data = True
            for f in range(a, b + 1):
                fp = os.path.join(out, "f%05d.png" % f)
                if os.path.exists(fp):          # another process has claimed it
                    continue
                open(fp, "w").close()
                sc.frame_set(f)
                update(f)
                sc.render.filepath = fp
                bpy.ops.render.render(write_still=True)
                pf.log("SAVED", fp)
            pf.log("FRAMES DONE %d-%d" % (a, b))
        else:
            for f in (int(x) for x in arg("pick", "1").split(",")):
                sc.frame_set(f)
                update(f)
                render_still(sc, arg("name", "film") + "_f%05d" % f)
    else:
        update(1)
        render_still(sc, arg("name", arg("view") or ("photo" if cam.photo_pose() else "hero")))
    pf.log("total %.1f s" % (time.time() - t0))


main()
