#!/usr/bin/env python3
"""Cinematic V2 polish for KIKO AND THE RUNAWAY FRUIT.

Loads the approved KIKO V1.1 asset without modifying its model or rig.
"""
from __future__ import annotations
import json, math, random, sys
from pathlib import Path
import bpy
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
import kiko_runaway_fruit as v1

ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/"output"/"kiko_runaway_fruit_30s_v2"; FRAMES=OUT/"frames"; REVIEW=ROOT/"review"/"kiko_runaway_fruit_v2"

def parent_keep(o,p):
    w=o.matrix_world.copy(); o.parent=p; o.matrix_world=w

def cylinder(name,a,b,r,ma,verts=10):
    a,b=Vector(a),Vector(b); d=b-a
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts,radius=r,depth=d.length,location=(a+b)/2)
    o=bpy.context.object; o.name=name; o.rotation_mode="QUATERNION"; o.rotation_quaternion=d.to_track_quat("Z","Y"); o.data.materials.append(ma); return o

def cinematic_environment(cam):
    rng=random.Random(731)
    # Existing lightweight clearing first, then layered depth additions.
    v1.environment()
    sky=v1.mat("V2_sky",(.34,.25,.22),.95); distant=v1.mat("V2_distant",(.055,.12,.105),1); cliff=v1.mat("V2_cliff",(.16,.17,.13),.96)
    leaf_a=v1.mat("V2_leaf_deep",(.025,.20,.085),.92); leaf_b=v1.mat("V2_leaf_gold",(.28,.42,.075),.92); rock=v1.mat("V2_rock",(.20,.23,.19),.98); flower=v1.mat("V2_flower",(.85,.16,.23),.8)
    # Warm backdrop and distant cliff/mountain silhouettes.
    v1.cube("V2_sky_backdrop",(0,10,4.0),(12,.18,5),sky,.02)
    for i,x in enumerate((-8,-5,-2,1,4,7)):
        v1.ell(f"V2_mountain_{i}",(x,8.8,2.2+rng.uniform(-.2,.3)),(3.0+rng.random(),.45,2.3+rng.random()),cliff)
    for layer,y in enumerate((7.8,6.7)):
        for i in range(10):
            x=-9+i*2+rng.uniform(-.45,.45); s=rng.uniform(.65,1.25)*(1 if layer else .8)
            v1.ell(f"V2_distant_canopy_{layer}_{i}",(x,y,2.3+rng.uniform(-.2,.5)),(1.2*s,.55,.9*s),distant if layer==0 else leaf_a)
    # Midground rocks, broad-leaf clusters, vines, flowers, grass and deadfall.
    for i in range(14):
        x=rng.uniform(-6,6); y=rng.uniform(1.7,6.0); s=rng.uniform(.16,.42)
        v1.ell(f"V2_rock_{i}",(x,y,s*.48),(s*1.5,s,s*.72),rock)
    for i in range(16):
        x=rng.uniform(-6,6); y=rng.uniform(1.4,5.7); base=rng.uniform(.12,.35)
        for j in range(rng.randint(3,5)):
            ang=(j/(4))*math.tau+rng.uniform(-.25,.25); o=v1.ell(f"V2_leaf_{i}_{j}",(x+math.cos(ang)*base,y+math.sin(ang)*base,.30+rng.random()*.22),(.38+rng.random()*.20,.08,.18+rng.random()*.10),leaf_a if (i+j)%2 else leaf_b)
            o.rotation_euler=(rng.uniform(-.35,.35),rng.uniform(-.35,.35),ang)
    for i in range(18):
        x=rng.uniform(-6,6); y=rng.uniform(.8,6.0); h=rng.uniform(.18,.48)
        cylinder(f"V2_grass_stem_{i}",(x,y,0),(x+rng.uniform(-.08,.08),y,h),.012,leaf_a,6)
    for i in range(9):
        x=rng.uniform(-5,5); y=rng.uniform(1.0,5.3)
        cylinder(f"V2_flower_stem_{i}",(x,y,0),(x,y,.34),.012,leaf_a,6); v1.ell(f"V2_flower_{i}",(x,y,.37),(.07,.045,.07),flower)
    cylinder("V2_fallen_branch",(-4,3,.12),(-1.7,3.4,.18),.09,v1.mat("V2_branch",(.13,.055,.02),.95),9)
    # Curved-looking hanging vines from short linked sections.
    vine=v1.mat("V2_vine",(.055,.25,.065),.95)
    for i,x in enumerate((-4.8,-2.3,3.4,5.1)):
        pts=[(x,5.4,5.0),(x+.12,5.3,4.25),(x-.10,5.2,3.55),(x+.16,5.1,2.9)]
        for j in range(3): cylinder(f"V2_vine_{i}_{j}",pts[j],pts[j+1],.025,vine,7)
    # Camera-edge foliage: parented to camera, deliberately sparse and soft.
    for side in (-1,1):
        for i in range(2):
            o=v1.ell(f"V2_foreground_leaf_{side}_{i}",(side*(2.8+i*.35),-4.6,.55+i*2.6),(.75,.08,.32),leaf_a)
            o.rotation_euler=(0,.15,side*(.55+i*.2))
    # Replace V1 lighting with a softer golden-hour three-point setup.
    for n in ("JUNGLE_sun","JUNGLE_fill","KIKO_tail_rim"):
        o=bpy.data.objects.get(n)
        if o:bpy.data.objects.remove(o,do_unlink=True)
    sun_data=bpy.data.lights.new("V2_golden_key","SUN"); sun_data.energy=2.55; sun_data.angle=math.radians(18); sun_data.color=(1,.48,.20)
    sun=bpy.data.objects.new("V2_golden_key",sun_data); bpy.context.collection.objects.link(sun); sun.rotation_euler=(math.radians(34),math.radians(-24),math.radians(-38))
    fill_data=bpy.data.lights.new("V2_cool_fill","AREA"); fill_data.energy=920; fill_data.color=(.29,.48,.88); fill_data.shape="DISK"; fill_data.size=7
    fill=bpy.data.objects.new("V2_cool_fill",fill_data); bpy.context.collection.objects.link(fill); fill.location=(-4,-4,5); fill.rotation_euler=((Vector((0,0,1.4))-fill.location).to_track_quat("-Z","Y").to_euler())
    rim_data=bpy.data.lights.new("V2_warm_rim","AREA"); rim_data.energy=780; rim_data.color=(1,.22,.055); rim_data.shape="DISK"; rim_data.size=5
    rim=bpy.data.objects.new("V2_warm_rim",rim_data); bpy.context.collection.objects.link(rim); rim.location=(4,3.5,3.4); rim.rotation_euler=((Vector((0,0,1.25))-rim.location).to_track_quat("-Z","Y").to_euler())
    bpy.context.scene.world.color=(.045,.045,.035)

def cinematic_camera(cam):
    # Held sections with gentle push-ins and one-frame cuts.
    shots=[
      (1,60,(-5.0,-9.5,2.65),(-4.45,-8.8,2.45),(-1.15,0,1.45),52),
      (61,120,(-.9,-8.2,2.02),(-.75,-7.7,1.96),(-.45,0,1.40),55),
      (121,168,(3.0,-7.8,1.72),(2.70,-7.2,1.66),(.70,0,1.08),58),
      (169,240,(-1.7,-8.0,2.0),(-.75,-7.15,1.92),(.95,0,1.30),54),
      (241,300,(4.8,-7.2,1.70),(4.35,-6.65,1.63),(1.52,0,1.02),58),
      (301,360,(3.2,-8.3,2.18),(2.9,-7.6,2.10),(1.22,0,1.46),58),
    ]
    cam.animation_data_clear(); cam.data.animation_data_clear()
    for start,end,a,b,target,lens in shots:
        for f,loc in ((start,a),(end,b)):
            cam.location=loc; cam.rotation_euler=(Vector(target)-cam.location).to_track_quat("-Z","Y").to_euler(); cam.data.lens=lens+(2 if f==end else 0)
            cam.keyframe_insert("location",frame=f); cam.keyframe_insert("rotation_euler",frame=f); cam.data.keyframe_insert("lens",frame=f)
        # Hold previous pose through the frame before each new section.
        if start>1:
            prev=start-1; cam.location=a; cam.rotation_euler=(Vector(target)-cam.location).to_track_quat("-Z","Y").to_euler(); cam.data.lens=lens
            cam.keyframe_insert("location",frame=prev); cam.keyframe_insert("rotation_euler",frame=prev); cam.data.keyframe_insert("lens",frame=prev)

def polish_animation(arm,fruit,creature):
    # Eyes lead head, head leads chest during discovery.
    for f,x in ((52,0),(62,-.08),(70,-.16),(82,-.11),(96,0),(116,.08),(126,0)):
        v1.key_bone(arm,"eye_L",f,(0,0,x)); v1.key_bone(arm,"eye_R",f,(0,0,x))
    for f,r in ((54,0),(66,-.12),(78,-.30),(90,-.24),(108,-.08),(120,0)): v1.key_bone(arm,"head",f,(0,0,r))
    for f,r in ((64,0),(80,-.05),(96,-.10),(112,-.05),(120,0)): v1.key_bone(arm,"chest",f,(r,0,0))
    # Reach anticipation and small overshoot.
    for f,a,b in ((104,0,0),(116,.18,0),(126,-.72,-.28),(138,-1.05,-.52),(148,-.88,-.40),(160,0,0)):
        v1.key_bone(arm,"upperarm_R",f,(0,a*.15,a)); v1.key_bone(arm,"lowerarm_R",f,(0,b,0))
    # Chase lean/stride and stop overshoot/settle.
    for f,r in ((166,0),(174,-.16),(190,-.25),(222,-.23),(240,-.05),(248,.09),(260,-.03),(276,0)): v1.key_bone(arm,"spine_01",f,(r,0,0))
    for f,a in ((168,0),(178,.76),(190,-.72),(202,.78),(214,-.74),(226,.68),(240,0)):
        v1.key_bone(arm,"thigh_L",f,(a,0,0)); v1.key_bone(arm,"thigh_R",f,(-a,0,0)); v1.key_bone(arm,"upperarm_L",f,(-a*.72,0,0)); v1.key_bone(arm,"upperarm_R",f,(a*.72,0,0))
    # More readable tail silhouette: lateral bias plus phase-delayed follow-through.
    for i in range(1,7):
        bias=.08+i*.025
        keys=[(1,bias*.4),(36,-bias*.35),(60,bias*.35),(120,-bias*.3),(168,0),(180+i*2,bias*1.8),(198+i*2,-bias*1.55),(218+i*2,bias*1.45),(240,0),(250+i*2,-bias*2.2),(268+i*2,bias*1.25),(292,-bias*.35),(330,bias*.35),(360,0)]
        for f,a in keys:v1.key_bone(arm,f"tail_{i:02d}",f,(a*.35,a*.42,((-1)**i)*a))
    # Fruit anticipation, squash, hops, acceleration, overshoot and settle.
    fruit.animation_data_clear()
    fruit_keys=[(1,(0,-.25,.20),(1,1,1),0),(112,(0,-.25,.20),(1,1,1),0),(120,(0,-.25,.16),(1.16,1.10,.76),-.15),(128,(.18,-.23,.42),(.86,.88,1.16),1.2),(138,(.54,-.18,.18),(1.10,1.05,.84),3.8),(146,(.92,-.12,.37),(.90,.92,1.10),6.4),(158,(1.55,-.04,.18),(1.08,1.04,.88),10.2),(168,(2.10,.02,.21),(1,1,1),13.0),(178,(2.34,.02,.20),(.98,1,1.02),14.0),(190,(2.24,.02,.20),(1,1,1),13.6),(300,(2.24,.02,.20),(1,1,1),13.6),(320,(2.08,-.02,.27),(.92,.92,.92),14.5),(342,(2.02,-.04,.29),(.68,.68,.68),15.2),(360,(2.02,-.04,.27),(.48,.48,.48),15.8)]
    for f,loc,scale,r in fruit_keys:v1.key_obj(fruit,f,loc=loc,rot=(0,r,0),scale=scale)
    # Creature reveal and gentle eating nods.
    for f,r in ((246,0),(258,-.12),(270,.10),(300,0),(316,-.18),(326,.12),(338,-.18),(348,.10),(360,0)): v1.key_obj(creature,f,rot=(r,0,0))
    # Existing facial shapes: curious -> confused -> surprised -> determined -> smile.
    mouth=bpy.data.objects.get("KIKO_GEO_mouth")
    if mouth and mouth.data.shape_keys:
        blocks=mouth.data.shape_keys.key_blocks
        schedule={"curious":((40,0),(62,1),(96,0)),"confused":((88,0),(108,1),(126,0)),"surprised":((120,0),(132,.55),(156,0)),"determined":((164,0),(180,.75),(230,0)),"smile":((292,0),(314,1),(360,1))}
        for name,keys in schedule.items():
            if name in blocks:
                for f,val in keys: blocks[name].value=val; blocks[name].keyframe_insert("value",frame=f)

def render():
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/"KIKO_master_v1_1.blend")); arm=bpy.data.objects["KIKO_RIG_armature"]
    v1.add_alias_controls(arm); v1.beauty_touchups(arm); cam=bpy.data.objects["KIKO_CAM"]; cinematic_environment(cam); fruit,creature=v1.props(); v1.animate(arm,fruit,creature,cam); polish_animation(arm,fruit,creature); cinematic_camera(cam)
    scene=bpy.context.scene; scene.frame_start=1; scene.frame_end=360; scene.render.fps=12; scene.render.engine="BLENDER_EEVEE"; scene.render.resolution_x=960; scene.render.resolution_y=540; scene.render.resolution_percentage=100; scene.render.image_settings.file_format="PNG"; scene.render.image_settings.color_mode="RGB"; scene.render.film_transparent=False
    scene.view_settings.look="AgX - Medium High Contrast"; FRAMES.mkdir(parents=True,exist_ok=True); REVIEW.mkdir(parents=True,exist_ok=True); OUT.mkdir(parents=True,exist_ok=True); scene.render.filepath=str(FRAMES/"frame_")
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/"KIKO_runaway_fruit_v002.blend")); bpy.ops.render.render(animation=True); bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/"KIKO_runaway_fruit_v002.blend"))
    meta={"source_model":"KIKO_master_v1_1.blend","armature":arm.name,"model_changed":False,"source_fps":12,"source_resolution":[960,540],"frames":360,"version":"V2"}
    (OUT/"render_manifest.json").write_text(json.dumps(meta,indent=2))
if __name__=="__main__": render()
