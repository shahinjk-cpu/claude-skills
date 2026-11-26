"""Render a saved millimetre assembly snapshot for geometry review."""
import argparse
from pathlib import Path
import numpy as np
import trimesh
import bpy
from inspect_scene import reset_scene, render_preview
from prepare_vehicle import mesh_object


def load_parts(snapshot):
    arrays=np.load(snapshot)
    return {key[:-9]:trimesh.Trimesh(arrays[key],arrays[key[:-9]+"_faces"],process=False)
            for key in arrays.files if key.endswith("_vertices")}


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot",required=True,type=Path)
    parser.add_argument("--output",required=True,type=Path)
    parser.add_argument("--explode",action="store_true")
    a=parser.parse_args()
    reset_scene()
    parts=load_parts(a.snapshot)
    offsets={"hull":[0,0,0],"track_left":[0,24,-3],"track_right":[0,-24,-3],
             "turret":[0,0,30],"gun_group":[24,0,43],"missile_left":[0,32,38],"missile_right":[0,-32,38]}
    for name,mesh in parts.items():
        if a.explode:
            mesh.apply_translation(offsets.get(name,[0,0,0]))
        mesh_object(name,mesh)
    bpy.context.scene.unit_settings.system="METRIC"
    bpy.context.scene.unit_settings.scale_length=.001
    a.output.parent.mkdir(parents=True,exist_ok=True)
    render_preview(a.output,resolution=1600)
