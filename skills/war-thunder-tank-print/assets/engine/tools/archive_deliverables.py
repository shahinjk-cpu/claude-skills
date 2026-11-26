"""Archive the validated BMPT deliverables; exclude runtimes and work caches."""
from pathlib import Path
import hashlib
import json
import zipfile

from pipeline import PROJECT, verify_snapshot, verified_parts


def main():
    output=PROJECT/"outputs"/"ussr_bmpt_72_1_72"
    _,source_hash=verify_snapshot(PROJECT,"ussr_bmpt_72")
    checked_parts=verified_parts(output,source_hash,72,PROJECT/"recipes"/"ussr_bmpt_72.json")
    package=json.loads((output/"bambu"/"packaging_report.json").read_text())
    if len(package.get("parts",[]))!=7 or any(p.get("status")!="passed" for p in package["parts"]):
        raise ValueError("All seven sliced plates must pass before release")
    expected={p["name"]:hashlib.sha256((output/p["path"]).read_bytes()).hexdigest() for p in checked_parts}
    if {p["name"]:p.get("source_sha256") for p in package["parts"]}!=expected:
        raise ValueError("Packaged slices do not match the validated STL files")
    for part in package["parts"]:
        sliced=part["slice"]
        if not sliced.get("within_170mm_target") or not sliced.get("within_180mm_build_volume") or sliced.get("slicer_warnings"):
            raise ValueError(f"Slice acceptance failed: {part['name']}")
        for filename in (part["project"],sliced["sliced_file"]):
            with zipfile.ZipFile(filename) as archive:
                if archive.testzip():
                    raise ValueError(f"3MF CRC verification failed: {filename}")
                for entry in archive.namelist():
                    if entry.endswith(".gcode"):
                        if archive.read(entry+".md5").decode().strip().lower()!=hashlib.md5(archive.read(entry)).hexdigest():
                            raise ValueError(f"G-code checksum failed: {filename}")
    files=[PROJECT/"README.md",PROJECT/"recipes"/"ussr_bmpt_72.json"]
    files+=list((output/"stl").glob("*.stl"))
    files+=[output/name for name in ("bmpt72_1_72.blend","assembly_preview.png",
        "assembly_exploded.png","presentation_report.json","final_visual_review.json","print_report.json",
        "construction_audit.json","repair_audits.json")]
    files+=[p for p in (output/"bambu").rglob("*")
            if p.is_file() and (p.suffix.lower() in (".3mf",".png",".json"))]
    calibration=PROJECT/"calibration"
    files+=[p for p in calibration.rglob("*") if p.is_file()
            and p.suffix.lower() in (".stl",".3mf",".png",".json",".txt",".fcstd")]
    pantsir=PROJECT/"outputs"/"pantsir_1_72"
    files+=[pantsir/name for name in ("scale_check.json","pantsir_reference_1_72.blend",
                                    "pantsir_reference_preview.png")]
    files=sorted(set(files))
    missing=[str(p) for p in files if not p.is_file()]
    if missing:
        raise FileNotFoundError(missing)
    manifest={"vehicle":"ussr_bmpt_72","scale":72,"physical_print_verified":False,
              "files":{str(p.relative_to(PROJECT)).replace("\\","/"):
                  hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}
    target=PROJECT/"BMPT72_1-72_Druckpaket.zip"
    temporary=target.with_suffix(".zip.partial")
    with zipfile.ZipFile(temporary,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for path in files:
            archive.write(path,str(path.relative_to(PROJECT)).replace("\\","/"))
        archive.writestr("DELIVERY_MANIFEST.json",json.dumps(manifest,indent=2))
    with zipfile.ZipFile(temporary) as archive:
        if archive.testzip():
            raise ValueError("Archive CRC verification failed")
    temporary.replace(target)
    print(json.dumps({"archive":str(target),"files":len(files),"bytes":target.stat().st_size,
                      "sha256":hashlib.sha256(target.read_bytes()).hexdigest()},indent=2))


if __name__=="__main__":
    main()
