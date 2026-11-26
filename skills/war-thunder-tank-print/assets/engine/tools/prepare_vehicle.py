"""Prepare an explicitly reviewed vehicle recipe into printable millimetre parts."""
from __future__ import annotations
import argparse
import hashlib
import json
import re
from pathlib import Path

import bpy
import numpy as np
import trimesh
import manifold3d as md
from mathutils import Matrix, Vector
from inspect_scene import import_model, reset_scene, world_mesh, render_preview

IMPLEMENTATION_SHA256={name:hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                       for name in ("prepare_vehicle.py","mesh_repair.py","inspect_scene.py","stl_precision.py")}


def ancestry(obj):
    names=[]
    while obj:
        names.append(obj.name)
        obj=obj.parent
    return names


def group_source(input_path, recipe, scale):
    if hashlib.sha256(Path(input_path).read_bytes()).hexdigest()!=recipe["source_glb_sha256"]:
        raise ValueError("Source snapshot changed; recipe must be reviewed for the new geometry.")
    reset_scene()
    import_model(input_path)
    cfg=recipe["grouping"]
    required=[cfg[k] for k in ("turret_root","gun_root","missile_root","hull_core","track_left","track_right")]
    absent=[n for n in required if n not in bpy.data.objects]
    if absent:
        raise ValueError(f"Recipe nodes absent: {absent}")
    unit=1000.0/scale
    grouped={name:[] for name in ("hull","track_left","track_right","turret","gun_group","missile_left","missile_right")}
    membership={name:[] for name in grouped}
    origins={}
    for obj in list(bpy.context.scene.objects):
        origins[obj.name]=(np.asarray(obj.matrix_world.translation)*unit).tolist()
        if obj.type!="MESH":
            continue
        chain=ancestry(obj)
        mesh=world_mesh(obj)
        mesh.apply_scale(unit)
        if not len(mesh.faces):
            continue
        # Source transforms include a mirror; geometric normals are recalculated.
        mesh.merge_vertices(digits_vertex=3)
        mesh.remove_unreferenced_vertices()
        mesh.update_faces(mesh.unique_faces())
        mesh.update_faces(mesh.nondegenerate_faces())
        mesh.fix_normals(multibody=True)
        if cfg["missile_root"] in chain:
            group="missile_left" if mesh.centroid[1]>0 else "missile_right"
        elif cfg["gun_root"] in chain:
            group="gun_group"
        elif cfg["turret_root"] in chain:
            group="turret"
        elif obj.name==cfg["track_left"] or any(re.search(p,obj.name) for p in cfg["left_patterns"]):
            group="track_left"
        elif obj.name==cfg["track_right"] or any(re.search(p,obj.name) for p in cfg["right_patterns"]):
            group="track_right"
        else:
            group="hull"
        grouped[group].append((obj.name,mesh))
        membership[group].append(obj.name)
    if any(not items for items in grouped.values()):
        raise ValueError("A required print group is empty.")
    return grouped,membership,origins


def mesh_object(name,mesh):
    data=bpy.data.meshes.new(name)
    data.from_pydata(mesh.vertices.tolist(),[],mesh.faces.tolist())
    data.update()
    obj=bpy.data.objects.new(name,data)
    bpy.context.collection.objects.link(obj)
    return obj


def repair_source(groups, out, target):
    from mesh_repair import repair_mesh, cache_compatible
    import mesh_repair
    cache=out/"repaired_objects"
    cache.mkdir(exist_ok=True)
    implementation=hashlib.sha256(Path(mesh_repair.__file__).read_bytes()).hexdigest()
    # Older numerical output is identical where every component passes the
    # new bounded-expansion guard. Outliers must run the corrected repair.
    compatible_implementations=[implementation,
        "6e470093a4c73eb147f49698aa0a21f4e6d2175d19aad89218ebad740107c775",
        "81dd672e65b823e24058288b1d513d1f63a824c8eb4b97ed67e4ce2bb9d45cb1"]
    repaired={name:[] for name in groups}
    audits={}
    for group,items in groups.items():
        for name,mesh in items:
            safe=re.sub(r"[^A-Za-z0-9_.-]","_",name)
            signature=hashlib.sha256(mesh.vertices.tobytes()+mesh.faces.tobytes()+implementation.encode()+str(target).encode()).hexdigest()
            compatible_signatures={hashlib.sha256(mesh.vertices.tobytes()+mesh.faces.tobytes()+impl.encode()+str(target).encode()).hexdigest():impl for impl in compatible_implementations}
            path=cache/f"{safe}.npz"
            audit_path=cache/f"{safe}.json"
            cached_audit=json.loads(audit_path.read_text()) if audit_path.exists() else None
            if (path.exists() and cached_audit
                and cached_audit.get("cache_signature") in compatible_signatures
                and cache_compatible(cached_audit,target)):
                arr=np.load(path)
                result=trimesh.Trimesh(arr["vertices"],arr["faces"],process=False)
                audit=json.loads(audit_path.read_text())
                audit["repair_implementation_sha256"]=compatible_signatures[audit["cache_signature"]]
                print(f"CACHED {group}/{name}",flush=True)
            else:
                print(f"REPAIR {group}/{name}: {len(mesh.faces)} triangles",flush=True)
                try:
                    result,audit=repair_mesh(mesh,target_mm=target,label=name)
                except ValueError as error:
                    # Intermediate objects are stored as float64 NPZ, not STL.
                    # If only STL rounding creates microscopic cracks, defer
                    # that conversion until the group has been fused/simplified.
                    candidate=getattr(error,"unquantized_mesh",None)
                    if candidate is None or not candidate.is_volume:
                        raise
                    result=candidate
                    audit=error.audit
                    audit.update(result_bounds_mm=result.bounds.tolist(),result_faces=len(result.faces),
                        result_volume_mm3=float(result.volume),result_watertight=bool(result.is_watertight),
                        result_components=len(result.split(only_watertight=False)),
                        maximum_bounds_change_mm=float(np.abs(result.bounds-mesh.bounds).max()),
                        stl_quantization_deferred_until_final_union=True)
                    print(f"FLOAT64 intermediate retained for {name}; final STL readback remains mandatory.",flush=True)
                audit["cache_signature"]=signature
                np.savez_compressed(path,vertices=result.vertices,faces=result.faces)
                audit_path.write_text(json.dumps(audit,indent=2),encoding="utf-8")
                print(f"REPAIRED {name}: {len(result.faces)} triangles, {audit['result_components']} shells",flush=True)
            repaired[group].append((name,result))
            audits[name]=audit
    return repaired,audits


def manifold(mesh):
    solid=md.Manifold(md.Mesh64(np.array(mesh.vertices,dtype=np.float64,order="C",copy=True),
                               np.array(mesh.faces,dtype=np.uint64,order="C",copy=True)))
    if solid.status()!=md.Error.NoError or solid.is_empty():
        raise ValueError(f"Invalid solid passed to Boolean: {solid.status()}")
    return solid


def from_manifold(solid):
    from mesh_repair import _trimesh
    if solid.status()!=md.Error.NoError or solid.is_empty():
        raise ValueError(f"Boolean failure: {solid.status()}")
    return _trimesh(solid)


def union(meshes):
    return from_manifold(md.Manifold.batch_boolean([manifold(m) for m in meshes],md.OpType.Add))


def difference(mesh, cutters):
    return from_manifold(md.Manifold.batch_boolean([manifold(mesh)]+[manifold(c) for c in cutters],md.OpType.Subtract))


def box(low, high):
    low,high=np.asarray(low),np.asarray(high)
    result=trimesh.creation.box(high-low)
    result.apply_translation((high+low)/2)
    return result


def cylinder_between(start,end,radius,sections=48):
    start,end=np.asarray(start),np.asarray(end)
    vector=end-start
    transform=trimesh.geometry.align_vectors([0,0,1],vector)
    transform[:3,3]=(start+end)/2
    return trimesh.creation.cylinder(radius,float(np.linalg.norm(vector)),sections=sections,transform=transform)


def clip_above(mesh,z):
    low=mesh.bounds[0]-1
    low[2]=z
    return from_manifold(manifold(mesh)^manifold(box(low,mesh.bounds[1]+1)))


def running_gear_backplate(track, sign, factor=1.0):
    """Keep the inner glue plate inside the rounded belt silhouette."""
    from shapely.geometry import MultiPoint, box as polygon_box
    outline=MultiPoint(np.asarray(track.vertices)[:,[0,2]]).convex_hull
    outline=outline.buffer(-.6*factor).intersection(
        polygon_box(-38*factor,2.7*factor,43*factor,13*factor))
    if outline.is_empty or outline.geom_type!="Polygon":
        raise ValueError("Running-gear outline cannot contain a continuous hidden backplate")
    plate=trimesh.creation.extrude_polygon(outline,2.0*factor,engine="earcut")
    transform=np.array([[1,0,0,0],[0,0,sign,sign*14.45*factor],
                        [0,1,0,0],[0,0,0,1]],dtype=float)
    plate.apply_transform(transform)
    return plate


def connect_shells(mesh,label,*,radius=.4,max_gap=5.0,_attempt=0):
    """Attach separated printable details with audited shortest local bridges."""
    from scipy.spatial import cKDTree
    shells=sorted(mesh.split(only_watertight=False),key=lambda m:abs(m.volume),reverse=True)
    audit={"part":label,"original_shells":len(shells),"bridges":[],"removed_unprintable_specks":[]}
    # Tiny standalone specks have no reproducible extrusion with a 0.2 mm nozzle.
    retained=[]
    for shell in shells:
        if abs(shell.volume)<.002 and max(shell.extents)<.3:
            audit["removed_unprintable_specks"].append({"volume_mm3":float(shell.volume),"bounds":shell.bounds.tolist()})
        else:
            retained.append(shell)
    if not retained:
        raise ValueError(f"{label}: no substantial geometry")
    connected=retained.pop(0)
    members=[connected]
    connected_vertices=connected.vertices.copy()
    bridge_meshes=[]
    while retained:
        tree=cKDTree(connected_vertices)
        choices=[]
        for i,shell in enumerate(retained):
            distances,indices=tree.query(shell.vertices,k=1)
            j=int(np.argmin(distances))
            choices.append((float(distances[j]),i,shell.vertices[j],connected_vertices[indices[j]]))
        distance,index,p,q=min(choices,key=lambda c:c[0])
        if distance>max_gap:
            raise ValueError(f"{label}: disconnected structural shell {distance:.3f} mm away; requires reviewed attachment")
        shell=retained.pop(index)
        direction=(q-p)/distance if distance>1e-5 else connected.centroid-shell.centroid
        if np.linalg.norm(direction)<1e-8:
            direction=np.array([0.,0.,1.])
        direction=direction/np.linalg.norm(direction)
        bridge=cylinder_between(p-direction*.35,q+direction*.35,radius,24)
        members.append(shell)
        bridge_meshes.append(bridge)
        connected_vertices=np.vstack((connected_vertices,shell.vertices))
        audit["bridges"].append({"start":p.tolist(),"end":q.tolist(),"gap_mm":distance,"diameter_mm":radius*2})
    connected=union(members+bridge_meshes) if bridge_meshes else connected
    final_shells=connected.split(only_watertight=False)
    substantial=[]
    for shell in final_shells:
        if abs(shell.volume)<.002 and max(shell.extents)<.8:
            audit["removed_unprintable_specks"].append({"generated_by_union":True,"volume_mm3":float(shell.volume),"bounds":shell.bounds.tolist()})
        else:
            substantial.append(shell)
    if len(substantial)!=len(final_shells):
        connected=trimesh.util.concatenate(substantial)
    remaining=len(substantial)
    if remaining>1 and _attempt<2:
        print(f"RECONNECT {label}: {remaining} shells, bridge diameter {2*(radius+.1):.1f} mm",flush=True)
        connected,retry=connect_shells(connected,label,radius=radius+.1,max_gap=max_gap,_attempt=_attempt+1)
        audit["bridges"].extend(retry["bridges"])
        audit["removed_unprintable_specks"].extend(retry["removed_unprintable_specks"])
        remaining=retry["final_shells"]
    if remaining!=1:
        summary=[{"volume":float(s.volume),"bounds":s.bounds.tolist()} for s in substantial]
        raise ValueError(f"{label}: attachment check left {remaining} shells: {summary}")
    audit["final_shells"]=remaining
    return connected,audit


def build_parts(groups,origins,recipe):
    parts={}
    audit={"reinforcements":[],"attachments":[],"joints":{}}
    for name,items in groups.items():
        print(f"UNION {name}",flush=True)
        solid=md.Manifold.batch_boolean([manifold(m) for _,m in items],md.OpType.Add)
        parts[name]=from_manifold(solid.simplify(.01))
    # Explicitly measured bearing geometry; all connector dimensions remain mm
    # when the source model scale changes.
    factor=recipe["scale_denominator"]/recipe.get("requested_scale",72)
    center=np.array(origins[recipe["grouping"]["turret_root"]])
    x,y=center[:2]
    trim=20.0*factor
    seat=trim-.30
    radius=14.2*factor
    parts["turret"]=clip_above(parts["turret"],trim)
    # Remove any repaired cap above the intended bearing surface inside its rim.
    clearance=cylinder_between([x,y,seat],[x,y,100*factor],radius)
    parts["hull"]=difference(parts["hull"],[clearance])
    cap=cylinder_between([x,y,seat-4.2],[x,y,seat],radius)
    # The bearing pad supports the actual seated pose, while the outer disc
    # clears the deck by 0.30 mm. Without it the turret would drop by that gap.
    bearing_pad=cylinder_between([x,y,seat],[x,y,trim],5.0,96)
    parts["hull"]=union([parts["hull"],cap,bearing_pad])
    disk=cylinder_between([x,y,trim],[x,y,trim+.8],radius)
    hub=cylinder_between([x,y,trim],[x,y,25.8*factor],4.0)
    j=recipe["joints"]
    pin_r=j["turret_pin_diameter_mm"]/2
    pin_tip=trim+j["turret_pin_engagement_mm"]
    chamfer=j["pin_tip_chamfer_mm"]
    pin=cylinder_between([x,y,seat-1.0],[x,y,pin_tip-chamfer],pin_r,96)
    tip=from_manifold(md.Manifold.cylinder(chamfer,pin_r,pin_r-chamfer,96).translate([x,y,pin_tip-chamfer]))
    parts["hull"]=union([parts["hull"],pin,tip])
    parts["turret"]=union([parts["turret"],disk,hub])
    socket=cylinder_between([x,y,trim-1],[x,y,trim+j["turret_bore_depth_mm"]],pin_r+j["turret_radial_clearance_mm"],96)
    parts["turret"]=difference(parts["turret"],[socket])
    audit["joints"]["turret"]={"axis_xy_mm":[float(x),float(y)],"trim_z_mm":trim,
        "seat_z_mm":seat,"radial_clearance_mm":j["turret_radial_clearance_mm"],
        "pin_diameter_mm":pin_r*2,"engagement_mm":j["turret_pin_engagement_mm"],
        "bore_depth_mm":j["turret_bore_depth_mm"],"outer_disc_clearance_mm":.3,
        "bearing_pad_diameter_mm":10.0,"bearing_pad_top_z_mm":trim,"pin_owner":"hull"}
    audit["reinforcements"].append("Internal turret basket removed; concealed bearing disk and hub added.")
    # Two inner backplates strengthen running gear and provide flat glue faces.
    for side,sign in (("left",1),("right",-1)):
        track_name=recipe["grouping"][f"track_{side}"]
        track=next(m for label,m in groups[f"track_{side}"] if label==track_name)
        plate=running_gear_backplate(track,sign,factor)
        parts[f"track_{side}"]=union([parts[f"track_{side}"],plate])
    audit["reinforcements"].append("Concealed 2-mm running-gear backplates create flat glue faces; rounded belt silhouette inset by 0.6 mm.")
    saddle=box(np.array([-19,-6.4,28])*factor,np.array([-15,6.4,31])*factor)
    shoulder=box(np.array([-18.55,-1.05,31])*factor,np.array([-15.45,1.05,33.3])*factor)
    parts["turret"]=union([parts["turret"],saddle])
    parts["gun_group"]=union([parts["gun_group"],shoulder])
    for side,sign in (("left",1),("right",-1)):
        low=np.array([-14.2,11.6,33.15])*factor
        high=np.array([-9.8,15.0,36.55])*factor
        if sign<0:
            low[1],high[1]=-high[1],-low[1]
        parts[f"missile_{side}"]=union([parts[f"missile_{side}"],box(low,high)])
    audit["reinforcements"].append("Concealed gun saddle/shoulder and reinforced pod receiver bosses added.")
    # Model-specific glue keys are loaded from the reviewed recipe.
    for connector in recipe.get("glue_keys",[]):
        fixed,moving=connector["fixed"],connector["moving"]
        low=np.array(connector["low_mm"])*factor
        high=np.array(connector["high_mm"])*factor
        key=box(low,high)
        parts[fixed]=union([parts[fixed],key])
        tolerance=j["glue_clearance_per_side_mm"]
        expanded=box(low-tolerance,high+tolerance)
        parts[moving]=difference(parts[moving],[expanded])
        audit["joints"][f"{fixed}_to_{moving}"]={"type":"keyed_glue","key_bounds_mm":[low.tolist(),high.tolist()],
                                 "clearance_per_side_mm":tolerance}
    for name,mesh in parts.items():
        print(f"ATTACH {name}",flush=True)
        parts[name],entry=connect_shells(mesh,name)
        audit["attachments"].append(entry)
    return parts,audit


def relieve_turret_ring(parts,audit,settings):
    """Machine concealed mating faces with a reviewed rotational profile."""
    x,y=audit["joints"]["turret"]["axis_xy_mm"]
    profile=settings["radius_profile_z_r_mm"]
    clearance=settings["radial_clearance_mm"]
    top=profile[-1][0]
    def revolved(points):
        segments=[md.Manifold.cylinder(z1-z0,r0,r1,256).translate([x,y,z0])
                  for (z0,r0),(z1,r1) in zip(points,points[1:])]
        return md.Manifold.batch_boolean(segments,md.OpType.Add)
    # A true overlap avoids a microscopic Boolean seam at the upper plane.
    allowed=revolved(profile+[[top+.05,profile[-1][1]]])
    allowed=allowed+manifold(box([-200,-200,top],[200,200,200]))
    original_turret=manifold(parts["turret"])
    turret=original_turret^allowed
    hole=revolved([[z,r+clearance] for z,r in profile])
    core_radius=settings["protected_bearing_radius_mm"]
    protected=md.Manifold.cylinder(200,core_radius,core_radius,128).translate([x,y,0])
    original_hull=manifold(parts["hull"])
    hull=original_hull-(hole-protected)
    parts["hull"],parts["turret"]=from_manifold(hull),from_manifold(turret)
    audit["turret_ring_relief"]={**settings,
        "removed_hull_volume_mm3":float(original_hull.volume()-hull.volume()),
        "removed_turret_volume_mm3":float(original_turret.volume()-turret.volume()),
        "purpose":"Restore rotation gap after reinforcement; preserve fixed outer collar and upper turret details",
        "upper_boolean_overlap_mm":.05}


def fit_and_check(parts,audit,recipe=None):
    """Eliminate authored interpenetration and verify the working turret envelope."""
    audit.pop("rotation_check",None)
    fit=[]
    # Game meshes can overlap. Receiver bodies are relieved against the actual
    # attached solid; designed socket clearances already exist independently.
    for receiver,insert in (("hull","track_left"),("hull","track_right"),
                            ("turret","gun_group"),("turret","missile_left"),("turret","missile_right")):
        a,b=manifold(parts[receiver]),manifold(parts[insert])
        overlap=a^b
        volume=abs(float(overlap.volume()))
        if volume>.001:
            parts[receiver]=from_manifold(a-b)
        fit.append({"receiver":receiver,"insert":insert,"relieved_overlap_mm3":volume})
    audit["assembly_reliefs"]=fit
    if recipe and recipe.get("turret_ring_relief"):
        ring=dict(recipe["turret_ring_relief"])
        ring["radial_clearance_mm"]=max(ring["radial_clearance_mm"],
            recipe["joints"]["turret_radial_clearance_mm"]+ring["minimum_eccentric_margin_mm"])
        relieve_turret_ring(parts,audit,ring)
    hull_shells=parts["hull"].split(only_watertight=False)
    retained=[]
    removed=[]
    for shell in hull_shells:
        b=shell.bounds
        hidden_stub=(abs(shell.volume)<.2 and max(shell.extents)<2.5
                     and np.abs(b[:,0]).max()<44 and np.abs(b[:,1]).max()<17
                     and b[:,2].max()<13)
        if hidden_stub:
            removed.append({"volume_mm3":float(shell.volume),"bounds_mm":b.tolist(),
                            "reason":"Hidden suspension stub isolated by running-gear backplate recess"})
        else:
            retained.append(shell)
    if removed:
        parts["hull"]=trimesh.util.concatenate(retained)
    audit["removed_hidden_recess_fragments"]=removed
    turret_shells=parts["turret"].split(only_watertight=False)
    retained=[]
    for shell in turret_shells:
        ring_top=audit.get("turret_ring_relief",{}).get("radius_profile_z_r_mm",[[0,0]])[-1][0]
        ring_edge=(abs(shell.volume)<.01 and max(shell.extents)<.8 and min(shell.extents)<.1
                   and abs(shell.bounds[0,2]-ring_top)<.001)
        if (abs(shell.volume)<.002 and max(shell.extents)<.8) or ring_edge:
            removed.append({"volume_mm3":float(shell.volume),"bounds_mm":shell.bounds.tolist(),
                            "reason":"Sub-extrusion edge fragment at machined turret ring" if ring_edge
                                     else "Sub-extrusion Boolean fragment at turret attachment interface"})
        else:
            retained.append(shell)
    if len(retained)!=len(turret_shells):
        parts["turret"]=trimesh.util.concatenate(retained)
    for name,mesh in parts.items():
        if not mesh.is_volume or len(mesh.split(only_watertight=False))!=1:
            shells=mesh.split(only_watertight=False)
            summary=[{"volume_mm3":float(s.volume),"bounds":s.bounds.tolist()} for s in shells]
            raise ValueError(f"{name}: assembly relief split the printable body; attachment requires revision: {summary}")
    return check_rotation(parts,audit)


def check_rotation(parts,audit):
    """Test nominal seating and maximum pin-play offsets across a full turn."""
    fixed=md.Manifold.batch_boolean([manifold(parts[n]) for n in ("hull","track_left","track_right")],md.OpType.Add)
    movable=md.Manifold.batch_boolean([manifold(parts[n]) for n in ("turret","gun_group","missile_left","missile_right")],md.OpType.Add)
    x,y=audit["joints"]["turret"]["axis_xy_mm"]
    checks=[]
    play=audit["joints"]["turret"]["radial_clearance_mm"]
    for dx,dy in ((0,0),(play,0),(-play,0),(0,play),(0,-play)):
        for degrees in range(0,360,15):
            moved=movable.translate([-x,-y,0]).rotate([0,0,degrees]).translate([x+dx,y+dy,0])
            clash=fixed^moved
            volume=abs(float(clash.volume())) if not clash.is_empty() else 0.0
            checks.append({"degrees":degrees,"eccentric_offset_xy_mm":[dx,dy],"intersection_mm3":volume})
    audit["rotation_check"]={"step_degrees":15,"samples":checks,
                              "maximum_intersection_mm3":max(c["intersection_mm3"] for c in checks),
                              "continuous_rotation_proven":False}
    if audit["rotation_check"]["maximum_intersection_mm3"]>.01:
        raise ValueError(f"Turret rotation collision: {audit['rotation_check']['maximum_intersection_mm3']:.4f} mm3; see construction audit")
    audit["rotation_check"]["sampled_angles_passed"]=True
    return parts


def dump_parts(parts,out,stem):
    packed={}
    for name,mesh in parts.items():
        packed[f"{name}_vertices"]=mesh.vertices
        packed[f"{name}_faces"]=mesh.faces
    np.savez_compressed(out/"work"/f"{stem}.npz",**packed)


def validate_and_export(parts,audit,source_report,recipe,out):
    from mesh_repair import _sample_thickness
    from stl_precision import prepare_stl_mesh
    output_stl=out/"stl"
    output_stl.mkdir(exist_ok=True)
    report={"vehicle_id":recipe["vehicle_id"],"source_sha256":recipe["source_glb_sha256"],
            "recipe_sha256":recipe["_recipe_sha256"],
            "profile":recipe["profile"],"implementation_sha256":IMPLEMENTATION_SHA256,
            "scale_denominator":recipe["requested_scale"],"geometry_passed":False,
            "physical_print_verified":False,"physical_calibration_passed":False,
            "parts":[],"construction":audit,
            "minimum_wall_target_mm":recipe["minimum_structural_thickness_mm"],
            "minimum_wall_thickness_globally_certified":False,
            "limitations":["Small cosmetic relief may be below the structural 0.8-mm target.",
                           "Local reinforcement rounds thin covers and small muzzle openings.",
                           "Physical fit and surviving detail require the supplied PLA calibration print."]}
    reset_scene()
    assembly_collection=bpy.data.collections.new("Assembled BMPT-72 (mm)")
    bpy.context.scene.collection.children.link(assembly_collection)
    bpy.context.view_layer.active_layer_collection=bpy.context.view_layer.layer_collection.children[assembly_collection.name]
    transforms={"hull":np.eye(4),"turret":np.eye(4),
                "track_left":trimesh.transformations.rotation_matrix(np.pi/2,[1,0,0]),
                "track_right":trimesh.transformations.rotation_matrix(-np.pi/2,[1,0,0]),
                "gun_group":trimesh.transformations.rotation_matrix(-np.pi/2,[0,1,0]),
                "missile_left":trimesh.transformations.rotation_matrix(-np.pi/2,[1,0,0]),
                "missile_right":trimesh.transformations.rotation_matrix(np.pi/2,[1,0,0])}
    actual_parts={}
    for name,mesh in parts.items():
        original=mesh
        reduction=[]
        for tolerance in (.01,.001,.0001):
            candidate=from_manifold(manifold(original).simplify(tolerance))
            connected=candidate.is_volume and len(candidate.split(only_watertight=False))==1
            reduction.append({"tolerance_mm":tolerance,"closed_connected":bool(connected)})
            if connected:
                mesh=candidate
                break
        else:
            mesh=original
        if not mesh.is_volume or len(mesh.split(only_watertight=False))!=1:
            raise ValueError(f"{name}: final part is not one closed positive volume")
        printable=mesh.copy()
        transform=transforms[name].copy()
        printable.apply_transform(transform)
        translation=-printable.bounds[0]
        printable.apply_translation(translation)
        transform[:3,3]+=translation
        printable,stl_audit=prepare_stl_mesh(printable,max_displacement_mm=.001)
        target=output_stl/f"{name}.stl"
        printable.export(target)
        loaded=trimesh.load_mesh(target,process=True)
        loaded.remove_unreferenced_vertices()
        if not loaded.is_volume or len(loaded.split(only_watertight=False))!=1:
            raise ValueError(f"{name}: exported STL failed closed/connected readback")
        if max(loaded.extents[:2]+16)>170 or loaded.extents[2]>170:
            raise ValueError(f"{name}: part plus print reserve exceeds the 170-mm target")
        assembled=loaded.copy()
        assembled.apply_transform(np.linalg.inv(transform))
        actual_parts[name]=assembled
        mesh_object(name,assembled)
        report["parts"].append({"name":name,"exported_stl":f"stl/{name}.stl",
            "sha256":hashlib.sha256(target.read_bytes()).hexdigest(),
            "exported_stl_sha256":hashlib.sha256(target.read_bytes()).hexdigest(),
            "bounds_assembly_mm":assembled.bounds.tolist(),"print_dimensions_mm":loaded.extents.tolist(),
            "assembly_to_print_transform":transform.tolist(),"triangles":len(loaded.faces),
            "volume_mm3":float(loaded.volume),"watertight":True,"connected_components":1,
            "simplification_attempts":reduction,
            "sampled_thickness":_sample_thickness(loaded,128),"stl_precision":stl_audit})
    check_rotation(actual_parts,audit)
    audit["rotation_check"]["geometry_source"]="final_exported_stl_readback"
    bpy.context.scene.unit_settings.system="METRIC"
    bpy.context.scene.unit_settings.scale_length=.001
    bpy.context.scene.unit_settings.length_unit="MILLIMETERS"
    bpy.ops.wm.save_as_mainfile(filepath=str(out/f"bmpt72_1_{recipe['requested_scale']}.blend"))
    render_preview(out/"assembly_preview.png",resolution=1600)
    # A second image makes component assignment and assembly order reviewable.
    offsets={"hull":[0,0,0],"track_left":[0,24,-3],"track_right":[0,-24,-3],
             "turret":[0,0,30],"gun_group":[24,0,43],"missile_left":[0,32,38],"missile_right":[0,-32,38]}
    for obj in list(bpy.context.scene.objects):
        if obj.type in ("CAMERA","LIGHT"):
            bpy.data.objects.remove(obj,do_unlink=True)
        elif obj.name in offsets:
            obj.location+=Vector(offsets[obj.name])
    render_preview(out/"assembly_exploded.png",resolution=1600)
    report["geometry_passed"]=True
    (out/"construction_audit.json").write_text(json.dumps(audit,indent=2),encoding="utf-8")
    (out/"print_report.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input",type=Path,required=True)
    p.add_argument("--recipe",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--scale",type=int,default=72)
    p.add_argument("--inspect-only",action="store_true")
    p.add_argument("--repair-only",action="store_true")
    a=p.parse_args()
    out=a.output.resolve()
    out.mkdir(parents=True,exist_ok=True)
    if not a.inspect_only:
        (out/"print_report.json").write_text(json.dumps({"geometry_passed":False,
            "status":"preparing","physical_print_verified":False}),encoding="utf-8")
    recipe=json.loads(a.recipe.read_text(encoding="utf-8"))
    if recipe.get("vehicle_id")!=a.recipe.stem or recipe.get("profile")!="a1mini_02_pla":
        raise ValueError("Recipe vehicle ID/profile does not match supported preparation request")
    recipe["_recipe_sha256"]=hashlib.sha256(a.recipe.read_bytes()).hexdigest()
    if a.scale not in recipe.get("validated_scales",[recipe["scale_denominator"]]):
        raise ValueError(f"Recipe joints are reviewed only for {recipe.get('validated_scales')}; another scale needs reviewed connection dimensions.")
    groups,members,origins=group_source(a.input,recipe,a.scale)
    report={"source":str(a.input.resolve()),"scale":a.scale,"members":members,"origins":origins,"groups":{}}
    for name,items in groups.items():
        mesh=trimesh.util.concatenate([m for _,m in items])
        report["groups"][name]={"bounds_mm":mesh.bounds.tolist(),"faces":len(mesh.faces),"source_objects":len(items)}
    (out/"source_groups.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    if a.inspect_only:
        print(json.dumps(report["groups"],indent=2))
        return
    work=out/"work"
    work.mkdir(exist_ok=True)
    repaired,audits=repair_source(groups,work,recipe["minimum_structural_thickness_mm"])
    (out/"repair_audits.json").write_text(json.dumps(audits,indent=2),encoding="utf-8")
    if a.repair_only:
        print("All source meshes conservatively repaired.")
        return
    recipe["requested_scale"]=a.scale
    parts,construction=build_parts(repaired,origins,recipe)
    dump_parts(parts,out,"assembled_before_fit")
    try:
        parts=fit_and_check(parts,construction,recipe)
    finally:
        dump_parts(parts,out,"assembled_after_fit")
        (out/"construction_audit.json").write_text(json.dumps(construction,indent=2),encoding="utf-8")
    validate_and_export(parts,construction,report,recipe,out)


if __name__=="__main__":
    main()
