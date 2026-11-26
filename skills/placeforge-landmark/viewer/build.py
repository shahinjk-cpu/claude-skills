"""Inline the exported scene (web/data/scene.json + scene.bin.gz) into viewer/template.html -> <project>/web/index.html.
One self-contained file: opens by double-click, can be hosted anywhere (three.js comes from the jsDelivr CDN).

    python3 build.py <project dir>
"""
import base64, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    proj = os.path.abspath(sys.argv[1])
    data = os.path.join(proj, "web", "data")
    meta = open(os.path.join(data, "scene.json")).read()
    b64 = base64.b64encode(open(os.path.join(data, "scene.bin.gz"), "rb").read()).decode()
    t = open(os.path.join(HERE, "template.html")).read()
    title = json.loads(meta)["name"] + " 3D"
    out = t.replace("%%TITLE%%", title).replace("%%META%%", meta).replace("%%DATA%%", b64)
    dst = os.path.join(proj, "web", "index.html")
    open(dst, "w").write(out)
    print("viewer: %s (%.1f MB)" % (dst, len(out) / 1e6))


if __name__ == "__main__":
    main()
