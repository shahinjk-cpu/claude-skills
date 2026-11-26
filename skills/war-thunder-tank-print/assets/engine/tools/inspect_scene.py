"""Inspect imported vehicle geometry in Blender; preserve the input asset."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def import_model(path):
    path = Path(path).resolve()
    if path.suffix.lower() in (".glb", ".gltf"):
        bpy.ops.import_scene.gltf(filepath=str(path))
    elif path.suffix.lower() == ".obj":
        bpy.ops.wm.obj_import(filepath=str(path))
    elif path.suffix.lower() == ".blend":
        bpy.ops.wm.open_mainfile(filepath=str(path))
    else:
        raise ValueError(f"Unsupported input: {path.suffix}")


def world_mesh(obj):
    import trimesh
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    try:
        mesh.calc_loop_triangles()
        verts = np.array([evaluated.matrix_world @ v.co for v in mesh.vertices], dtype=float)
        faces = np.array([t.vertices[:] for t in mesh.loop_triangles], dtype=int)
        result = trimesh.Trimesh(verts, faces, process=True)
        result.remove_unreferenced_vertices()
        return result
    finally:
        evaluated.to_mesh_clear()


def render_preview(path, *, direction=(1.4, -1.7, 1.2), resolution=1400):
    """Neutral clay render of current mesh objects; Cycles CPU works headlessly."""
    objects = [o for o in bpy.context.scene.objects if o.type == "MESH" and not o.hide_render]
    corners = [o.matrix_world @ Vector(c) for o in objects for c in o.bound_box]
    low = Vector(tuple(min(p[i] for p in corners) for i in range(3)))
    high = Vector(tuple(max(p[i] for p in corners) for i in range(3)))
    center = (low + high) / 2
    extent = max(high - low)
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 24
    scene.cycles.use_denoising = True
    scene.render.resolution_x = resolution
    scene.render.resolution_y = int(resolution * .72)
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.world = bpy.data.worlds.new("Preview world")
    scene.world.use_nodes = True
    scene.world.node_tree.nodes["Background"].inputs["Color"].default_value = (.16,.19,.23,1)
    scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value = .65
    mat = bpy.data.materials.new("Neutral clay")
    mat.diffuse_color = (.42,.51,.36,1)
    mat.use_nodes = True
    mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (.42,.51,.36,1)
    mat.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = .72
    for obj in objects:
        obj.data.materials.clear()
        obj.data.materials.append(mat)
        for face in obj.data.polygons:
            face.material_index = 0
    bpy.ops.object.camera_add(location=center+Vector(direction).normalized()*extent*2.5)
    cam = bpy.context.object
    cam.rotation_euler = (center-cam.location).to_track_quat("-Z","Y").to_euler()
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = extent*1.3
    cam.data.clip_end = extent*20
    cam.data.clip_start = max(extent/10000, .00001)
    scene.camera = cam
    for location, energy, size in (((.5,-.8,1.7),800,1.1), ((-.8,.4,1.0),500,.9)):
        bpy.ops.object.light_add(type="AREA", location=center+Vector(location)*extent)
        light=bpy.context.object
        light.rotation_euler=(center-light.location).to_track_quat("-Z","Y").to_euler()
        light.data.energy=energy*extent*extent/25
        light.data.shape="DISK"
        light.data.size=size*extent
    scene.render.filepath=str(Path(path).resolve())
    bpy.ops.render.render(write_still=True)


def inspect(path, output, render=False):
    output=Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    reset_scene()
    import_model(path)
    report={"input":str(Path(path).resolve()),"blender_version":bpy.app.version_string,"objects":[]}
    bounds=[]
    for obj in bpy.context.scene.objects:
        row={"name":obj.name,"type":obj.type,"parent":obj.parent.name if obj.parent else None,
             "origin":list(obj.matrix_world.translation),"matrix_world":[list(r) for r in obj.matrix_world]}
        if obj.type=="MESH":
            mesh=world_mesh(obj)
            if len(mesh.vertices):
                bounds.append(mesh.bounds)
                row.update(vertices=len(mesh.vertices),faces=len(mesh.faces),bounds=mesh.bounds.tolist(),
                           extents=mesh.extents.tolist(),watertight=bool(mesh.is_watertight),
                           volume=float(mesh.volume),components=int(len(mesh.split(only_watertight=False))),
                           materials=[m.name for m in obj.data.materials if m])
        report["objects"].append(row)
    if bounds:
        b=np.array(bounds)
        report["bounds"]=[b[:,0].min(axis=0).tolist(),b[:,1].max(axis=0).tolist()]
        report["extents"]=(np.array(report["bounds"])[1]-report["bounds"][0]).tolist()
    (output/"scene_inventory.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    bpy.ops.wm.save_as_mainfile(filepath=str(output/"imported.blend"))
    if render:
        render_preview(output/"source_preview.png")
    print(json.dumps({"objects":len(report["objects"]),"extents":report.get("extents"),"out":str(output)}))


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--input",required=True)
    p.add_argument("--output",required=True)
    p.add_argument("--render",action="store_true")
    a=p.parse_args()
    inspect(a.input,a.output,a.render)
