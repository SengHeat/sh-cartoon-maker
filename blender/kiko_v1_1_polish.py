#!/usr/bin/env python3
"""Focused visual and motion polish for KIKO V1.1; preserves the V1 rig."""
from __future__ import annotations
import json, math
from pathlib import Path
import bpy
from mathutils import Vector

BLENDER_DIR=Path(__file__).resolve().parent; ROOT=BLENDER_DIR.parent; REVIEW=ROOT/"review"/"kiko_3d_v1_1"; OUT=ROOT/"output"/"kiko_3d_motion_test_v1_1"; MASTER=BLENDER_DIR/"KIKO_master_v1_1.blend"

def reshape_head():
    head=bpy.data.objects["KIKO_GEO_head"]
    for v in head.data.vertices:
        z=v.co.z
        # Wider upper skull/cheeks, narrower jaw; keep eye placement unchanged.
        if z<1.92: sx=.86
        elif z<2.22: sx=1.10
        elif z<2.50: sx=1.06
        else: sx=1.02
        v.co.x*=sx
        if 1.88<z<2.20: v.co.y*=1.06
    for side in ("L","R"):
        c=bpy.data.objects["KIKO_GEO_cheek_fluff_"+side]
        # Mesh coordinates are scene-space; expand from the inner cheek root.
        anchor=.26 if side=="L" else -.26
        for v in c.data.vertices:
            v.co.x=anchor+(v.co.x-anchor)*1.42
            v.co.z=2.08+(v.co.z-2.08)*1.17

def reshape_ears():
    for side,s in (("L",1),("R",-1)):
        for prefix in ("KIKO_GEO_ear_","KIKO_GEO_ear_inner_"):
            o=bpy.data.objects[prefix+side]; ax=s*.32; az=2.48
            for v in o.data.vertices:
                dx=v.co.x-ax; dz=v.co.z-az
                v.co.x=ax+dx*1.34+s*dz*.15
                v.co.z=az+dz*1.27
                v.co.y-=abs(dx)*.025

def crest_layers():
    # Enlarge the three existing clumps and derive two smaller overlapping clumps.
    bases=[bpy.data.objects[f"KIKO_GEO_crest_{i}"] for i in range(3)]
    for i,o in enumerate(bases):
        center=Vector(([-.18,0,.18][i],.02,[2.66,2.78,2.66][i]))
        for v in o.data.vertices: v.co=center+(v.co-center)*Vector((1.22,1.12,1.28))
    for idx,(source,dx,dz,scale) in enumerate(((bases[0],-.13,-.06,.78),(bases[2],.13,-.06,.78)),start=3):
        o=source.copy(); o.data=source.data.copy(); o.name=f"KIKO_GEO_crest_{idx}"; bpy.context.collection.objects.link(o)
        for v in o.data.vertices: v.co.x+=dx; v.co.z+=dz
        # Preserve armature, groups, and head weights from the source clone.

def soften_limbs():
    for side,s in (("L",1),("R",-1)):
        arm=bpy.data.objects["KIKO_GEO_arm_"+side]
        for v in arm.data.vertices:
            t=max(0,min(1,(1.55-v.co.z)/.65))
            # shoulder softness, elbow pinch, forearm flare/tuft
            factor=1.0-.12*math.exp(-((v.co.z-1.20)/.09)**2)+.14*max(0,(t-.55)/.45)
            v.co.x=s*(abs(v.co.x)*factor)
        leg=bpy.data.objects["KIKO_GEO_leg_"+side]
        for v in leg.data.vertices:
            # define knee and ankle while retaining sturdy cartoon volume
            factor=.90 if .36<v.co.z<.52 else (1.10 if .18<v.co.z<.34 else 1.0)
            v.co.x=s*(abs(v.co.x)*factor)
        hand=bpy.data.objects["KIKO_GEO_hand_"+side]
        for v in hand.data.vertices:
            # flattened soft paw instead of round mitten
            v.co.x=s*(abs(v.co.x)*1.08); v.co.y*=1.10
        foot=bpy.data.objects["KIKO_GEO_foot_"+side]
        for v in foot.data.vertices:
            if v.co.y<-.15: v.co.y*=1.13
            v.co.z=.10+(v.co.z-.10)*.84
    tail=bpy.data.objects["KIKO_GEO_tail_plume"]
    for v in tail.data.vertices:
        # Fuller middle plume, unchanged root for safe deformation.
        if .35<v.co.y<1.05: v.co.x*=1.13; v.co.z=.82+(v.co.z-.82)*1.06

def fur_roughness():
    for name in ("fur_gray","fur_cream","fur_orange"):
        m=bpy.data.materials.get(name)
        if not m or not m.use_nodes: continue
        nt=m.node_tree; bs=nt.nodes.get("Principled BSDF")
        noise=nt.nodes.get("V1.1 micro roughness") or nt.nodes.new("ShaderNodeTexNoise"); noise.name="V1.1 micro roughness"; noise.inputs["Scale"].default_value=7; noise.inputs["Detail"].default_value=2; noise.inputs["Roughness"].default_value=.65
        ramp=nt.nodes.get("V1.1 roughness range") or nt.nodes.new("ShaderNodeValToRGB"); ramp.name="V1.1 roughness range"; ramp.color_ramp.elements[0].position=.22; ramp.color_ramp.elements[0].color=(.68,.68,.68,1); ramp.color_ramp.elements[1].position=.78; ramp.color_ramp.elements[1].color=(.94,.94,.94,1)
        nt.links.new(noise.outputs["Fac"],ramp.inputs["Fac"]); nt.links.new(ramp.outputs["Color"],bs.inputs["Roughness"])

def keybone(arm,n,f,rot=None,loc=None):
    p=arm.pose.bones[n]; p.rotation_mode="XYZ"
    if rot is not None: p.rotation_euler=rot; p.keyframe_insert("rotation_euler",frame=f)
    if loc is not None: p.location=loc; p.keyframe_insert("location",frame=f)

def keyobj(o,f,loc=None,scale=None):
    if loc is not None: o.location=loc; o.keyframe_insert("location",frame=f)
    if scale is not None: o.scale=scale; o.keyframe_insert("scale",frame=f)

def animate(arm):
    sc=bpy.context.scene; sc.frame_start=1; sc.frame_end=240; sc.render.fps=24
    arm.animation_data_clear(); arm.animation_data_create(); arm.animation_data.action=bpy.data.actions.new("KIKO_ACT_motion_test_v1_1")
    # Reset the preserved rig, then layer more exaggerated poses.
    for p in arm.pose.bones: p.rotation_mode="XYZ"; p.rotation_euler=(0,0,0); p.location=(0,0,0)
    # 0-2: clear breathing.
    for f,z,r in ((1,0,0),(12,.018,.015),(24,.045,.035),(36,.018,.015),(48,0,0)):
        keybone(arm,"spine_02",f,(r,0,0), (0,0,z)); keybone(arm,"chest",f,(-r*.55,0,0))
    # 2-4: unmistakable left/right head and eye aim.
    for f,r in ((48,0),(60,.48),(72,.58),(84,-.58),(92,-.48),(96,0)): keybone(arm,"head",f,(0,0,r))
    for f,x in ((48,0),(64,-.12),(76,0),(86,.12),(96,0)):
        keybone(arm,"eye_L",f,(0,0,x)); keybone(arm,"eye_R",f,(0,0,x))
    # Blink by lowering the upper lid arches, without scaling around world origin.
    for side in ("L","R"):
        lid=bpy.data.objects["KIKO_GEO_lid_"+side]
        for f,z in ((1,0),(26,0),(28,-.16),(31,0),(68,0),(70,-.16),(73,0),(240,0)): keyobj(lid,f,loc=(0,0,z))
    # 4-6: right-hand wave, three clean arcs, plus smile.
    for f,a,b in ((96,0,0),(104,-1.50,-1.05),(112,-1.30,-.36),(120,-1.52,-1.08),(128,-1.30,-.34),(136,-1.52,-1.08),(142,-1.30,-.34),(144,0,0)):
        keybone(arm,"upperarm_R",f,(0,a*.18,-a)); keybone(arm,"lowerarm_R",f,(0,-b,0)); keybone(arm,"hand_R",f,(0,0,b*.35))
    mouth=bpy.data.objects["KIKO_GEO_mouth"]
    if mouth.data.shape_keys:
        smile=mouth.data.shape_keys.key_blocks["smile"]
        for f,v in ((96,0),(106,1),(140,1),(148,0)): smile.value=v; smile.keyframe_insert("value",frame=f)
    # 6-8: two planted steps, hip shift, opposition and forward travel.
    for f,x,z in ((144,0,0),(156,.13,.035),(168,.27,0),(180,.41,.035),(192,.55,0)): keyobj(arm,f,loc=(x,0,z))
    for f,hip in ((144,0),(156,.16),(168,-.14),(180,.16),(192,0)): keybone(arm,"pelvis",f,(0,hip*.35,hip))
    for f,a in ((144,0),(154,.62),(166,-.55),(178,.62),(190,-.55),(192,0)):
        keybone(arm,"thigh_L",f,(a,0,0)); keybone(arm,"thigh_R",f,(-a,0,0)); keybone(arm,"upperarm_L",f,(-a*.62,0,0)); keybone(arm,"upperarm_R",f,(a*.62,0,0))
    for f,zl,zr in ((144,0,0),(154,.12,0),(166,0,.12),(178,.12,0),(190,0,.12),(192,0,0)):
        keybone(arm,"IK_foot_L",f,loc=(0,0,zl)); keybone(arm,"IK_foot_R",f,loc=(0,0,zr))
    for i in range(1,7):
        for f,a in ((144,0),(156+i*2,.10+i*.018),(170+i*2,-.08),(182+i*2,.09),(192,0)): keybone(arm,f"tail_{i:02d}",f,(a,0,((-1)**i)*a*.25))
    # 8-10: strong upright recoil and delayed settle, never a crouch.
    for f,x,z in ((192,.55,0),(202,.43,.16),(212,.46,.13),(228,.50,.055),(240,.55,0)): keyobj(arm,f,loc=(x,0,z))
    for f,r in ((192,0),(202,-.28),(214,-.20),(228,-.08),(240,0)): keybone(arm,"spine_01",f,(r,0,0)); keybone(arm,"head",f,(-r*.45,0,0))
    for side,s in (("L",1),("R",-1)):
        for f,r in ((192,0),(202,s*.22),(218,s*.13),(240,0)): keybone(arm,"ear_01_"+side,f,(0,r,s*r*.25))
    for i in range(1,7):
        for f,a in ((192,0),(200+i*2,-.30-i*.045),(214+i*2,.18+i*.02),(230+i,-.08),(240,0)): keybone(arm,f"tail_{i:02d}",f,(a,0,((-1)**i)*a*.28))
    # Brows rise, eyes enlarge and mouth opens using stable object transforms.
    for side in ("L","R"):
        brow=bpy.data.objects["KIKO_GEO_brow_"+side]; eye=bpy.data.objects["KIKO_GEO_eye_"+side]; iris=bpy.data.objects["KIKO_GEO_iris_"+side]
        for f,z in ((192,0),(202,.10),(220,.075),(240,0)): keyobj(brow,f,loc=(0,0,z))
        for f,s in ((192,1),(202,1.12),(220,1.08),(240,1)): keyobj(eye,f,scale=(1,1,s)); keyobj(iris,f,scale=(1,1,s))
    for f,s in ((192,1),(202,1.65),(222,1.42),(240,1)): keyobj(mouth,f,scale=(1,1,s))

def render_reviews(cam):
    REVIEW.mkdir(parents=True,exist_ok=True); sc=bpy.context.scene; sc.render.engine="BLENDER_EEVEE"; sc.render.resolution_x=700; sc.render.resolution_y=700; sc.render.resolution_percentage=100; sc.render.image_settings.file_format="PNG"; sc.frame_set(1)
    for n,loc,target,lens in (("front",(0,-5.8,1.62),(0,0,1.50),58),("three_quarter",(3.8,-4.6,1.75),(0,0,1.52),58),("face_closeup",(0,-3.65,2.34),(0,0,2.27),72)):
        cam.location=loc; cam.rotation_euler=(Vector(target)-cam.location).to_track_quat("-Z","Y").to_euler(); cam.data.lens=lens; sc.render.filepath=str(REVIEW/(n+".png")); bpy.ops.render.render(write_still=True)

def render_motion(cam):
    OUT.mkdir(parents=True,exist_ok=True); frames=OUT/"frames"; frames.mkdir(parents=True,exist_ok=True); sc=bpy.context.scene
    sc.render.resolution_x=854; sc.render.resolution_y=480; sc.render.resolution_percentage=100; sc.render.image_settings.file_format="PNG"; sc.render.image_settings.color_mode="RGB"
    cam.location=(3.8,-6.3,1.85); cam.rotation_euler=(Vector((.25,0,1.48))-cam.location).to_track_quat("-Z","Y").to_euler(); cam.data.lens=60; sc.render.filepath=str(frames/"frame_"); bpy.ops.render.render(animation=True)

def main():
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/"KIKO_master_v002.blend")); arm=bpy.data.objects["KIKO_RIG_armature"]
    reshape_head(); reshape_ears(); crest_layers(); soften_limbs(); fur_roughness(); animate(arm); cam=bpy.data.objects["KIKO_CAM"]
    arm["kiko_asset_version"]="production-v1.1"; bpy.ops.wm.save_as_mainfile(filepath=str(MASTER)); render_reviews(cam); bpy.ops.wm.save_as_mainfile(filepath=str(MASTER)); render_motion(cam); bpy.ops.wm.save_as_mainfile(filepath=str(MASTER))
    report={"version":"V1.1","rig":arm.name,"vertices":sum(len(o.data.vertices) for o in bpy.data.objects if o.type=="MESH"),"polygons":sum(len(o.data.polygons) for o in bpy.data.objects if o.type=="MESH"),"rig_rebuilt":False,"source":"KIKO_master_v002.blend"}
    (REVIEW/"build_report.json").write_text(json.dumps(report,indent=2))
if __name__=="__main__": main()
