#!/usr/bin/env python3
"""Final readability corrections for V1.1 wave and surprise."""
from pathlib import Path
import bpy

path=Path(__file__).resolve().parent/"KIKO_master_v1_1.blend"; bpy.ops.wm.open_mainfile(filepath=str(path)); arm=bpy.data.objects["KIKO_RIG_armature"]
# Three alternating forearm arcs, layered onto the preserved action.
p=arm.pose.bones["lowerarm_R"]; p.rotation_mode="XYZ"
for f,x in ((96,0),(104,-.72),(112,.55),(120,-.72),(128,.55),(136,-.72),(142,.55),(144,0)):
    p.rotation_euler=(x,0,0); p.keyframe_insert("rotation_euler",frame=f)
# Stable open-mouth oval used only for the surprised reaction.
mouth=bpy.data.objects.get("KIKO_GEO_surprise_mouth")
if not mouth:
    bpy.ops.mesh.primitive_uv_sphere_add(segments=20,ring_count=12,location=(0,-.605,1.985)); mouth=bpy.context.object; mouth.name="KIKO_GEO_surprise_mouth"; mouth.scale=(.115,.018,.095); bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    mouth.data.materials.append(bpy.data.materials["mouth"])
    for poly in mouth.data.polygons: poly.use_smooth=True
    w=mouth.matrix_world.copy(); mouth.parent=arm; mouth.parent_type="BONE"; mouth.parent_bone="head"; mouth.matrix_world=w
for f,s in ((1,.001),(192,.001),(200,.65),(204,1.0),(220,.88),(234,.52),(240,.001)):
    mouth.scale=(s,s,s); mouth.keyframe_insert("scale",frame=f)
bpy.ops.wm.save_as_mainfile(filepath=str(path))
