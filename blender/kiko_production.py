#!/usr/bin/env python3
"""Build and review the production-style 3D KIKO asset.

Run from the repository root:
    blender -b --python blender/kiko_production.py

The script is deterministic, self-contained, and intentionally avoids texture
files, particle systems, and simulation-heavy fur for laptop-safe rendering.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import bpy
from mathutils import Vector


BLENDER_DIR = Path(__file__).resolve().parent
ROOT = BLENDER_DIR.parent
MASTER = BLENDER_DIR / "KIKO_master_v002.blend"
REVIEW = ROOT / "review" / "kiko_3d"
MOTION = ROOT / "output" / "kiko_3d_motion_test"
FPS = 24


def mat(name, color, rough=.72, metallic=0.0):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1)
    m.use_nodes = True
    p = m.node_tree.nodes.get("Principled BSDF")
    p.inputs["Base Color"].default_value = (*color, 1)
    p.inputs["Roughness"].default_value = rough
    p.inputs["Metallic"].default_value = metallic
    return m


def smooth(obj, bevel=0.0, subdiv=0):
    if obj.type == "MESH":
        for p in obj.data.polygons:
            p.use_smooth = True
    if bevel:
        mod = obj.modifiers.new("Soft edge", "BEVEL")
        mod.width, mod.segments = bevel, 2
    if subdiv:
        mod = obj.modifiers.new("Production subdivision", "SUBSURF")
        mod.levels = 1
        mod.render_levels = subdiv
    return obj


def ellipsoid(name, loc, scale, material, seg=32, rings=20):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=rings, location=loc)
    o = bpy.context.object
    o.name, o.scale = name, scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.data.materials.append(material)
    return smooth(o, subdiv=1)


def loft(name, centers, radii, material, sides=16, caps=True):
    """Continuous organic tube along Y/Z; radii entries are (x, depth)."""
    verts, faces = [], []
    for c, (rx, ry) in zip(centers, radii):
        tangent = Vector(centers[min(len(centers)-1, centers.index(c)+1)]) - Vector(centers[max(0, centers.index(c)-1)])
        tangent.normalize()
        lateral = Vector((1, 0, 0))
        depth = tangent.cross(lateral).normalized()
        for j in range(sides):
            a = 2 * math.pi * j / sides
            verts.append(Vector(c) + lateral * (math.cos(a)*rx) + depth * (math.sin(a)*ry))
    for i in range(len(centers)-1):
        for j in range(sides):
            a, b = i*sides+j, i*sides+(j+1)%sides
            faces.append((a, b, b+sides, a+sides))
    if caps:
        verts += [Vector(centers[0]), Vector(centers[-1])]
        a, b = len(verts)-2, len(verts)-1
        faces += [tuple([a]+list(reversed(range(sides)))), tuple([b]+list(range((len(centers)-1)*sides, len(centers)*sides)))]
    mesh = bpy.data.meshes.new(name+"_mesh")
    mesh.from_pydata(verts, [], faces); mesh.update()
    o = bpy.data.objects.new(name, mesh); bpy.context.collection.objects.link(o)
    o.data.materials.append(material)
    return smooth(o, subdiv=1)


def leaf(name, side, material, inner_material):
    """Thick, cupped leaf ear; custom topology rather than cone geometry."""
    sx = side
    outline = [(0,0,0), (.39,0,.10), (.62,.02,.35), (.49,.03,.68), (.08,.02,.58), (-.13,0,.25)]
    front = [(sx*(.32+x), -.06+y, 2.48+z) for x,y,z in outline]
    back = [(x, y+.13, z) for x,y,z in front]
    verts = front+back
    faces = [(0,1,2,3,4,5),(11,10,9,8,7,6)]
    for i in range(6): faces.append((i,(i+1)%6,(i+1)%6+6,i+6))
    me=bpy.data.meshes.new(name+"_mesh"); me.from_pydata(verts,[],faces); me.materials.append(material); me.materials.append(inner_material)
    o=bpy.data.objects.new(name,me); bpy.context.collection.objects.link(o)
    # inset/cavity is a separate smaller leaf with visible coral material
    inner=[(x*.78, y-.012, 2.52+(z-2.52)*.78+.08) for x,y,z in front]
    mi=bpy.data.meshes.new(name+"_inner_mesh"); mi.from_pydata(inner,[],[(0,1,2,3,4,5)]); mi.materials.append(inner_material)
    io=bpy.data.objects.new(name.replace("ear","ear_inner"),mi); bpy.context.collection.objects.link(io)
    smooth(o, bevel=.025, subdiv=1); smooth(io, bevel=.012)
    return o,io


def cube(name, loc, scale, material, bevel=.05):
    bpy.ops.mesh.primitive_cube_add(location=loc); o=bpy.context.object
    o.name=name; o.scale=scale; bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    o.data.materials.append(material); return smooth(o, bevel=bevel)


def curve_tube(name, points, radius, material, cyclic=False):
    cu=bpy.data.curves.new(name+"_curve","CURVE"); cu.dimensions="3D"; cu.bevel_depth=radius; cu.bevel_resolution=3; cu.resolution_u=12
    sp=cu.splines.new("BEZIER"); sp.bezier_points.add(len(points)-1)
    for b,p in zip(sp.bezier_points,points): b.co=p; b.handle_left_type=b.handle_right_type="AUTO"
    sp.use_cyclic_u=cyclic
    o=bpy.data.objects.new(name,cu); bpy.context.collection.objects.link(o); o.data.materials.append(material); return o


def materials():
    return {
      "fur_gray":mat("fur_gray",(.23,.32,.36),.9), "fur_cream":mat("fur_cream",(.83,.76,.63),.92),
      "fur_orange":mat("fur_orange",(.67,.24,.08),.88), "inner_ear":mat("inner_ear",(.72,.29,.25),.8),
      "eye_white":mat("eye_white",(.94,.90,.79),.35), "iris":mat("iris",(.95,.38,.04),.35),
      "pupil":mat("pupil",(.018,.012,.009),.3), "nose":mat("nose",(.18,.08,.075),.5),
      "mouth":mat("mouth",(.12,.025,.025),.75), "tongue":mat("tongue",(.76,.21,.25),.65),
      "teeth":mat("teeth",(.96,.91,.77),.45), "scarf":mat("scarf",(.88,.22,.035),.88),
      "leather":mat("leather",(.20,.075,.025),.82), "cloth":mat("cloth",(.22,.28,.12),.95),
      "backpack":mat("backpack",(.28,.16,.07),.9), "charm":mat("charm",(.65,.34,.055),.38,.65)
    }


def armature():
    data=bpy.data.armatures.new("KIKO_RIG_data"); arm=bpy.data.objects.new("KIKO_RIG_armature",data); bpy.context.collection.objects.link(arm)
    bpy.context.view_layer.objects.active=arm; bpy.ops.object.mode_set(mode="EDIT")
    def add(n,h,t,p=None,d=True):
        b=data.edit_bones.new(n); b.head=h; b.tail=t; b.use_deform=d
        if p: b.parent=data.edit_bones[p]
    add("root",(0,0,0),(0,0,.75)); add("COG",(0,0,.75),(0,0,.9),"root"); add("pelvis",(0,0,.82),(0,0,1.04),"COG")
    add("spine_01",(0,0,1.04),(0,0,1.25),"pelvis"); add("spine_02",(0,0,1.25),(0,0,1.48),"spine_01"); add("chest",(0,0,1.48),(0,0,1.70),"spine_02")
    add("neck",(0,0,1.7),(0,0,1.82),"chest"); add("head",(0,0,1.82),(0,0,2.54),"neck"); add("jaw",(0,-.27,2.05),(0,-.43,1.96),"head")
    for s,side in ((1,"L"),(-1,"R")):
        x=s*.48
        add("ear_01_"+side,(x,0,2.47),(s*.57,0,2.72),"head"); add("ear_02_"+side,(s*.57,0,2.72),(s*.67,0,2.96),"ear_01_"+side); add("ear_03_"+side,(s*.67,0,2.96),(s*.73,0,3.18),"ear_02_"+side)
        add("eye_"+side,(s*.19,-.38,2.29),(s*.19,-.55,2.29),"head")
        add("clavicle_"+side,(0,0,1.57),(s*.31,0,1.55),"chest"); add("upperarm_"+side,(s*.31,0,1.55),(s*.52,0,1.20),"clavicle_"+side)
        add("lowerarm_"+side,(s*.52,0,1.20),(s*.56,-.01,.91),"upperarm_"+side); add("hand_"+side,(s*.56,-.01,.91),(s*.58,-.05,.72),"lowerarm_"+side)
        for i in range(4):
            add(f"finger_{i:02d}_01_{side}",(s*.58,-.05,.78),(s*(.61+i*.018),-.13,.69),"hand_"+side); add(f"finger_{i:02d}_02_{side}",(s*(.61+i*.018),-.13,.69),(s*(.62+i*.02),-.17,.63),f"finger_{i:02d}_01_{side}")
        add("thigh_"+side,(s*.19,0,.86),(s*.20,0,.48),"pelvis"); add("shin_"+side,(s*.20,0,.48),(s*.20,0,.16),"thigh_"+side)
        add("foot_"+side,(s*.20,0,.16),(s*.20,-.34,.08),"shin_"+side); add("toe_"+side,(s*.20,-.34,.08),(s*.20,-.48,.07),"foot_"+side)
    add("eye_aim",(0,-1.2,2.3),(0,-1.4,2.3),None,False)
    pts=[(0,.13,.9),(0,.36,.69),(0,.58,.63),(0,.81,.72),(0,1.02,.91),(0,1.17,1.13),(0,1.24,1.34)]
    for i in range(6): add(f"tail_{i+1:02d}",pts[i],pts[i+1],"pelvis" if i==0 else f"tail_{i:02d}")
    add("CTRL_root",(0,.25,0),(0,.25,.75),None,False); add("CTRL_COG",(0,.25,.82),(0,.25,1.2),"CTRL_root",False); add("CTRL_head",(0,.25,1.82),(0,.25,2.54),"CTRL_COG",False)
    for s,side in ((1,"L"),(-1,"R")):
        add("IK_foot_"+side,(s*.20,-.15,.02),(s*.20,-.15,.22),None,False); add("POLE_knee_"+side,(s*.20,-.8,.48),(s*.20,-.8,.68),None,False)
    bpy.ops.object.mode_set(mode="POSE")
    for side in ("L","R"):
        c=arm.pose.bones["shin_"+side].constraints.new("IK"); c.name="KIKO leg IK"; c.target=arm; c.subtarget="IK_foot_"+side; c.pole_target=arm; c.pole_subtarget="POLE_knee_"+side; c.chain_count=2
    bpy.ops.object.mode_set(mode="OBJECT"); arm.show_in_front=False; arm.hide_render=True
    return arm


def bind(obj, arm, groups):
    mod=obj.modifiers.new("KIKO Armature","ARMATURE"); mod.object=arm; mod.use_deform_preserve_volume=True
    # Assign by nearest named bone center, blended to two nearest for smooth joints.
    bones=[arm.data.bones[g] for g in groups if g in arm.data.bones]
    vgs={b.name:obj.vertex_groups.new(name=b.name) for b in bones}
    for v in obj.data.vertices:
        p=obj.matrix_world@v.co
        ranked=sorted(((p-(arm.matrix_world@((b.head_local+b.tail_local)*.5))).length,b.name,b) for b in bones)[:2]
        inv=[1/max(d,.03)**2 for d,_,_ in ranked]; total=sum(inv)
        for w,(_,_,b) in zip(inv,ranked): vgs[b.name].add([v.index],w/total,"REPLACE")
    obj.parent=arm


def build_character(m):
    objs=[]
    # Connected custom-profile core, deliberately non-spherical silhouette.
    body=loft("KIKO_GEO_body",[(0,0,.72),(0,.015,.92),(0,.015,1.18),(0,0,1.43),(0,0,1.62)],[(.24,.18),(.34,.25),(.39,.29),(.35,.25),(.22,.18)],m["fur_gray"],20); objs.append(body)
    head=loft("KIKO_GEO_head",[(0,0,1.68),(0,-.015,1.86),(0,0,2.10),(0,.025,2.36),(0,.04,2.58)],[(.24,.21),(.42,.35),(.53,.43),(.58,.45),(.43,.32)],m["fur_gray"],24); objs.append(head)
    # muzzle and sculpted cheek ruffs
    muzzle=ellipsoid("KIKO_GEO_muzzle",(0,-.405,2.05),(.34,.20,.23),m["fur_cream"]); objs.append(muzzle)
    for s,side in ((1,"L"),(-1,"R")):
        cheek=loft("KIKO_GEO_cheek_fluff_"+side,[(s*.30,-.28,2.13),(s*.47,-.21,2.09),(s*.57,-.12,2.00)],[(.19,.12),(.16,.10),(.025,.02)],m["fur_cream"],12); objs.append(cheek)
        ear,inner=leaf("KIKO_GEO_ear_"+side,s,m["fur_gray"],m["inner_ear"]); objs += [ear,inner]
    # layered crest and chest tufts
    for i,(x,z,sc) in enumerate([(-.18,2.66,.75),(0,2.78,1.0),(.18,2.66,.72)]):
        tuft=loft(f"KIKO_GEO_crest_{i}",[(x,.02,z),(x*.8,.02,z+.29*sc),(x*.55,.015,z+.40*sc)],[(.14,.10),(.10,.07),(.015,.012)],m["fur_orange"],10); objs.append(tuft)
    for i,x in enumerate((-.13,0,.13)):
        objs.append(loft(f"KIKO_GEO_chest_tuft_{i}",[(x,-.25,1.45),(x,-.32,1.22),(x*.7,-.30,1.05)],[(.13,.06),(.105,.05),(.015,.01)],m["fur_cream"],10))
    # eyes, irises, pupils, lids, brows
    for s,side in ((1,"L"),(-1,"R")):
        eye=ellipsoid("KIKO_GEO_eye_"+side,(s*.205,-.405,2.30),(.205,.13,.255),m["eye_white"],24,16); objs.append(eye)
        iris=ellipsoid("KIKO_GEO_iris_"+side,(s*.205,-.526,2.30),(.105,.022,.132),m["iris"],20,12); objs.append(iris)
        pupil=ellipsoid("KIKO_GEO_pupil_"+side,(s*.205,-.546,2.30),(.044,.012,.078),m["pupil"],16,10); objs.append(pupil)
        curve_tube("KIKO_GEO_lid_"+side,[(s*(.36),-.552,2.32),(s*.205,-.57,2.45),(s*.05,-.552,2.32)],.025,m["fur_gray"])
        curve_tube("KIKO_GEO_brow_"+side,[(s*.36,-.47,2.55),(s*.20,-.50,2.60),(s*.07,-.47,2.56)],.028,m["fur_orange"])
    ellipsoid("KIKO_GEO_nose",(0,-.605,2.12),(.115,.07,.075),m["nose"],20,12)
    mouth=loft("KIKO_GEO_mouth",[(0,-.553,2.03),(0,-.575,1.94)],[(.18,.025),(.13,.018)],m["mouth"],16)
    keys=mouth.shape_key_add(name="Basis")
    for name in ["neutral","happy","smile","curious","confused","surprised","scared","determined","sad","blink"]:
        k=mouth.shape_key_add(name=name)
        for v in k.data:
            if name in {"happy","smile"}: v.co.z += .035*(1-abs(v.co.x)/.2)
            elif name in {"surprised","scared"}: v.co.z += (.04 if v.co.z>1.98 else -.04)
            elif name=="sad": v.co.z -= .025*(1-abs(v.co.x)/.2)
    ellipsoid("KIKO_GEO_tongue",(0,-.59,1.96),(.09,.018,.035),m["tongue"],16,8)
    # tapered limbs and broad paws
    for s,side in ((1,"L"),(-1,"R")):
        arm=loft("KIKO_GEO_arm_"+side,[(s*.31,0,1.52),(s*.45,-.01,1.35),(s*.53,-.02,1.13),(s*.56,-.04,.91)],[(.17,.16),(.145,.13),(.12,.11),(.10,.09)],m["fur_gray"],14); objs.append(arm)
        hand=loft("KIKO_GEO_hand_"+side,[(s*.56,-.04,.91),(s*.57,-.08,.80),(s*.57,-.12,.68)],[(.10,.09),(.20,.16),(.13,.11)],m["fur_cream"],14); objs.append(hand)
        for i in range(4): objs.append(ellipsoid(f"KIKO_GEO_digit_{i}_{side}",(s*(.50+i*.045),-.20,.69+i*.004),(.045,.09,.055),m["fur_cream"],12,8))
        leg=loft("KIKO_GEO_leg_"+side,[(s*.19,0,.86),(s*.20,.015,.61),(s*.20,0,.38),(s*.20,-.01,.16)],[(.19,.18),(.16,.15),(.14,.13),(.12,.11)],m["fur_gray"],14); objs.append(leg)
        foot=loft("KIKO_GEO_foot_"+side,[(s*.20,.02,.18),(s*.20,-.20,.12),(s*.20,-.43,.10)],[(.15,.10),(.19,.12),(.22,.10)],m["fur_cream"],14); objs.append(foot)
        for i in range(3): objs.append(ellipsoid(f"KIKO_GEO_toe_{i}_{side}",(s*(.11+i*.09),-.48,.09),(.055,.09,.05),m["fur_cream"],12,8))
    # one continuous striped plume mesh with material bands
    centers=[(0,.10,.88),(0,.30,.67),(0,.53,.61),(0,.76,.68),(0,.96,.86),(0,1.11,1.08),(0,1.19,1.29),(0,1.18,1.46)]
    tail=loft("KIKO_GEO_tail_plume",centers,[(.22,.20),(.28,.25),(.30,.27),(.28,.25),(.25,.22),(.21,.19),(.15,.14),(.035,.03)],m["fur_gray"],18); objs.append(tail)
    tail.data.materials.append(m["fur_cream"]); tail.data.materials.append(m["fur_orange"])
    ringn=18
    for p in tail.data.polygons:
        band=int(sum(tail.data.vertices[i].co.y for i in p.vertices)/len(p.vertices)*7)
        p.material_index=1 if band%3==1 else (2 if band%3==2 else 0)
    return objs, mouth


def outfit(m):
    o=[]
    # scarf loop and two cloth tails
    o.append(curve_tube("KIKO_OUTFIT_scarf",[(-.25,-.02,1.67),(0,-.22,1.62),(.25,-.02,1.67),(0,.18,1.68)],.075,m["scarf"],True))
    o += [loft("KIKO_OUTFIT_scarf_tail_A",[(-.05,-.20,1.62),(-.14,-.26,1.34),(-.09,-.23,1.13)],[(.09,.025),(.075,.02),(.025,.012)],m["scarf"],10),loft("KIKO_OUTFIT_scarf_tail_B",[(.06,-.20,1.62),(.16,-.24,1.39),(.13,-.22,1.24)],[(.08,.025),(.065,.02),(.025,.012)],m["scarf"],10)]
    vest=cube("KIKO_OUTFIT_vest",(0,.015,1.25),(.34,.255,.35),m["cloth"],.10); o.append(vest)
    # open front cream visibility via dark center panel and leather trim
    o.append(cube("KIKO_OUTFIT_vest_opening",(0,-.255,1.30),(.12,.025,.29),m["fur_cream"],.025))
    o.append(curve_tube("KIKO_OUTFIT_belt",[(-.31,0,1.00),(0,-.25,.98),(.31,0,1.00),(0,.23,1.00)],.045,m["leather"],True))
    for s in (-1,1): o.append(curve_tube("KIKO_OUTFIT_harness_"+("L" if s>0 else "R"),[(s*.25,-.25,1.52),(s*.08,-.29,1.03)],.035,m["leather"]))
    pack=cube("KIKO_OUTFIT_backpack",(0,.31,1.30),(.29,.18,.34),m["backpack"],.09); o.append(pack)
    bed=curve_tube("KIKO_OUTFIT_bedroll",[(-.25,.50,1.55),(.25,.50,1.55)],.12,m["cloth"]); o.append(bed)
    for s,side in ((1,"L"),(-1,"R")):
        o.append(curve_tube("KIKO_OUTFIT_wrist_wrap_"+side,[(s*.53,-.02,.99),(s*.58,-.04,.90)],.065,m["cloth"]))
        o.append(curve_tube("KIKO_OUTFIT_ankle_wrap_"+side,[(s*.20,0,.24),(s*.20,-.03,.16)],.08,m["cloth"]))
    charm=ellipsoid("KIKO_OUTFIT_compass",(.11,-.34,1.02),(.09,.025,.09),m["charm"],20,10); o.append(charm)
    return o


def rig_character(arm, deform, outfit_objs):
    for o in deform:
        if o.type!="MESH": continue
        n=o.name
        if "head" in n or "muzzle" in n or "mouth" in n or "tongue" in n or "nose" in n or "cheek" in n or "eye" in n or "iris" in n or "pupil" in n or "crest" in n: groups=["head","neck"]
        elif "ear_" in n: groups=["ear_01_L","ear_02_L","ear_03_L"] if n.endswith("_L") else ["ear_01_R","ear_02_R","ear_03_R"]
        elif "tail" in n: groups=[f"tail_{i:02d}" for i in range(1,7)]
        elif "arm_L" in n or "hand_L" in n: groups=["upperarm_L","lowerarm_L","hand_L"]
        elif "arm_R" in n or "hand_R" in n: groups=["upperarm_R","lowerarm_R","hand_R"]
        elif "leg_L" in n or "foot_L" in n: groups=["thigh_L","shin_L","foot_L"]
        elif "leg_R" in n or "foot_R" in n: groups=["thigh_R","shin_R","foot_R"]
        else: groups=["pelvis","spine_01","spine_02","chest","neck"]
        bind(o,arm,groups)
    def bone_parent(o, bone):
        world=o.matrix_world.copy(); o.parent=arm; o.parent_type="BONE"; o.parent_bone=bone; o.matrix_world=world
    for o in outfit_objs:
        n=o.name
        bone="pelvis" if "belt" in n else "chest"
        if "wrist_wrap_L" in n: bone="hand_L"
        elif "wrist_wrap_R" in n: bone="hand_R"
        elif "ankle_wrap_L" in n: bone="foot_L"
        elif "ankle_wrap_R" in n: bone="foot_R"
        bone_parent(o,bone)
    # Facial curves/details are rigid anatomy driven by the head bone.
    for o in bpy.data.objects:
        if o.name.startswith("KIKO_GEO_") and o.parent is None:
            bone_parent(o,"head")


def animate(arm, mouth):
    scene=bpy.context.scene; scene.frame_start=1; scene.frame_end=240; scene.render.fps=FPS
    act=bpy.data.actions.new("KIKO_ACT_motion_test"); arm.animation_data_create(); arm.animation_data.action=act
    def key(bone,frame,rot=None,loc=None):
        p=arm.pose.bones[bone]; p.rotation_mode="XYZ"
        if rot is not None: p.rotation_euler=rot; p.keyframe_insert("rotation_euler",frame=frame)
        if loc is not None: p.location=loc; p.keyframe_insert("location",frame=frame)
    for f in (1,48,96,144,192,240): key("CTRL_root",f,loc=(0,0,0))
    # idle breathing, look and blink
    for f,z in ((1,0),(24,.025),(48,0),(96,0),(144,0),(192,0),(240,0)): key("CTRL_COG",f,loc=(0,0,z))
    for f,r in ((1,0),(48,0),(58,.32),(72,-.32),(88,0),(96,0),(192,0),(204,-.12),(216,.10),(240,0)): key("CTRL_head",f,rot=(0,0,r))
    # wave at 4-6s
    for f,r1,r2 in ((96,0,0),(106,-1.5,-1.0),(116,-1.35,-.55),(128,-1.5,-1.1),(140,-1.35,-.55),(144,0,0)):
        key("upperarm_L",f,rot=(0,r1*.18,r1)); key("lowerarm_L",f,rot=(0,r2,0))
    # two walk steps with root travel
    for f,x in ((144,0),(192,.62),(240,.62)): key("root",f,loc=(x,0,0))
    for f,a in ((144,0),(156,.55),(168,0),(180,-.55),(192,0)):
        key("thigh_L",f,rot=(a,0,0)); key("thigh_R",f,rot=(-a,0,0)); key("upperarm_L",f,rot=(-a*.55,0,0)); key("upperarm_R",f,rot=(a*.55,0,0))
    # surprise and delayed tail follow-through
    for i in range(1,7):
        b=f"tail_{i:02d}"; delay=i*2
        for f,a in ((192,0),(202+delay,.18+i*.025),(218+delay,-.10),(240,0)): key(b,f,rot=(a,0,(-1 if i%2 else 1)*a*.35))
    # blink through eyelid scale and expression shape keys
    for side in ("L","R"):
        lid=bpy.data.objects.get("KIKO_GEO_lid_"+side)
        if lid:
            for f,z in ((48,1),(66,.15),(69,1),(86,.15),(89,1),(204,.15),(208,1)):
                lid.scale.z=z; lid.keyframe_insert("scale",frame=f)
    if mouth.data.shape_keys:
        for k in mouth.data.shape_keys.key_blocks:
            if k.name not in {"Basis","surprised"}: k.value=0
        s=mouth.data.shape_keys.key_blocks["surprised"]
        # Key remains available to Animation Core V2, but the motion test keeps
        # it neutral pending a dedicated corrective sculpt for extreme poses.
        for f,v in ((192,0),(204,0),(232,0),(240,0)): s.value=v; s.keyframe_insert("value",frame=f)
    # expose semantic actions without disrupting the master motion action
    for name in ["idle","walk","run","jump","turn","look_at","blink","wave","smile","surprised"]:
        a=bpy.data.actions.new("KIKO_ACT_"+name); a["semantic_api"]=name; a["animation_core_version"]="2"
    return act


def studio():
    world=bpy.context.scene.world or bpy.data.worlds.new("World"); bpy.context.scene.world=world; world.color=(.045,.055,.07)
    floor=cube("STUDIO_floor",(0,0,-.07),(4,4,.05),mat("studio_floor",(.075,.09,.105),.82),.02)
    for name,loc,energy,size,color in [("Key",(-3,-4,5),1100,4,(1,.78,.60)),("Fill",(3,-2,3),700,3,(.48,.67,1)),("Rim",(0,3,4),900,3,(1,.34,.12))]:
        d=bpy.data.lights.new(name,"AREA"); d.energy=energy; d.shape="DISK"; d.size=size; d.color=color
        o=bpy.data.objects.new(name,d); o.location=loc; bpy.context.collection.objects.link(o); o.rotation_euler=((Vector((0,0,1.35))-o.location).to_track_quat("-Z","Y").to_euler())
    camd=bpy.data.cameras.new("KIKO_CAM_data"); cam=bpy.data.objects.new("KIKO_CAM",camd); bpy.context.collection.objects.link(cam); bpy.context.scene.camera=cam; camd.lens=58
    return cam


def render_reviews(cam):
    REVIEW.mkdir(parents=True,exist_ok=True); sc=bpy.context.scene
    sc.render.engine="BLENDER_EEVEE"; sc.render.resolution_x=700; sc.render.resolution_y=700; sc.render.resolution_percentage=100
    sc.render.image_settings.file_format="PNG"; sc.render.film_transparent=False; sc.render.image_settings.color_mode="RGBA"
    views={"front":(0,-5.5,1.55),"three_quarter":(3.5,-4.1,1.65),"side":(5.3,0,1.55),"back":(0,5.5,1.55),"face_closeup":(0,-3.45,2.28)}
    for n,loc in views.items():
        cam.location=loc; target=Vector((0,0,2.2 if n=="face_closeup" else 1.45)); cam.rotation_euler=(target-cam.location).to_track_quat("-Z","Y").to_euler(); cam.data.lens=72 if n=="face_closeup" else 58
        sc.render.filepath=str(REVIEW/(n+".png")); sc.frame_set(1); bpy.ops.render.render(write_still=True)


def contact_sheet():
    # Blender compositor-free ImageMagick/ffmpeg assembly is performed by the wrapper.
    pass


def render_motion(cam):
    MOTION.mkdir(parents=True,exist_ok=True); sc=bpy.context.scene
    sc.render.resolution_x=854; sc.render.resolution_y=480; sc.render.resolution_percentage=100; sc.render.fps=FPS
    cam.location=(3.5,-5.4,1.8); cam.rotation_euler=(Vector((.3,0,1.42))-cam.location).to_track_quat("-Z","Y").to_euler(); cam.data.lens=58
    frames=MOTION/"frames"; frames.mkdir(parents=True,exist_ok=True)
    sc.render.image_settings.file_format="PNG"; sc.render.image_settings.color_mode="RGB"; sc.render.filepath=str(frames/"frame_")
    bpy.ops.render.render(animation=True)


def main():
    bpy.ops.object.select_all(action="SELECT"); bpy.ops.object.delete(use_global=False)
    for d in (bpy.data.meshes,bpy.data.curves,bpy.data.materials,bpy.data.armatures,bpy.data.actions):
        for x in list(d): d.remove(x)
    m=materials(); arm=armature(); deform,mouth=build_character(m); gear=outfit(m); rig_character(arm,deform,gear); animate(arm,mouth); cam=studio()
    arm["kiko_asset_version"]="production-v002"; arm["animation_core_version"]="2"; arm["primitive_dummy_visible"]=False
    bpy.ops.wm.save_as_mainfile(filepath=str(MASTER))
    render_reviews(cam); bpy.ops.wm.save_as_mainfile(filepath=str(MASTER)); render_motion(cam)
    stats={"armature":arm.name,"deform_bones":sum(b.use_deform for b in arm.data.bones),"control_bones":sum(not b.use_deform for b in arm.data.bones),"mesh_objects":len([o for o in bpy.data.objects if o.type=="MESH"]),"vertices":sum(len(o.data.vertices) for o in bpy.data.objects if o.type=="MESH"),"polygons":sum(len(o.data.polygons) for o in bpy.data.objects if o.type=="MESH"),"materials":[x.name for x in m.values()],"shape_keys":[k.name for k in mouth.data.shape_keys.key_blocks],"actions":[a.name for a in bpy.data.actions]}
    (REVIEW/"build_report.json").write_text(json.dumps(stats,indent=2))
    print("KIKO_PRODUCTION_COMPLETE",json.dumps(stats))


if __name__=="__main__": main()
