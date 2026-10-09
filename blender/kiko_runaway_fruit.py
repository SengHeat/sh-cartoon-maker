#!/usr/bin/env python3
"""Create and render the 30-second KIKO AND THE RUNAWAY FRUIT short."""
from __future__ import annotations
import math
import os
from pathlib import Path
import bpy
from mathutils import Vector

BLENDER_DIR=Path(__file__).resolve().parent; ROOT=BLENDER_DIR.parent; OUT=ROOT/"output"/"kiko_runaway_fruit_30s"; FRAMES=OUT/"frames"

def mat(name,c,rough=.8,emit=0):
    m=bpy.data.materials.get(name) or bpy.data.materials.new(name); m.diffuse_color=(*c,1); m.use_nodes=True
    p=m.node_tree.nodes.get("Principled BSDF"); p.inputs["Base Color"].default_value=(*c,1); p.inputs["Roughness"].default_value=rough
    if emit: p.inputs["Emission Color"].default_value=(*c,1); p.inputs["Emission Strength"].default_value=emit
    return m

def smooth(o):
    for p in getattr(o.data,"polygons",[]): p.use_smooth=True
    return o

def ell(name,loc,scale,ma,seg=16):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2,radius=1,location=loc); o=bpy.context.object; o.name=name; o.scale=scale; bpy.ops.object.transform_apply(location=False,rotation=False,scale=True); o.data.materials.append(ma); return smooth(o)

def cube(name,loc,scale,ma,bev=.08):
    bpy.ops.mesh.primitive_cube_add(location=loc); o=bpy.context.object; o.name=name; o.scale=scale; bpy.ops.object.transform_apply(location=False,rotation=False,scale=True); o.data.materials.append(ma)
    b=o.modifiers.new("soft","BEVEL"); b.width=bev; b.segments=2; return o

def key_obj(o,f,loc=None,rot=None,scale=None):
    if loc is not None: o.location=loc; o.keyframe_insert("location",frame=f)
    if rot is not None: o.rotation_euler=rot; o.keyframe_insert("rotation_euler",frame=f)
    if scale is not None: o.scale=scale; o.keyframe_insert("scale",frame=f)

def key_bone(arm,n,f,rot=(0,0,0),loc=None):
    p=arm.pose.bones.get(n)
    if not p:return
    p.rotation_mode="XYZ"; p.rotation_euler=rot; p.keyframe_insert("rotation_euler",frame=f)
    if loc is not None: p.location=loc; p.keyframe_insert("location",frame=f)

def add_alias_controls(arm):
    aliases={"CTRL_ROOT":"CTRL_root","CTRL_BODY":"CTRL_COG","CTRL_HEAD":"CTRL_head","CTRL_HAND.L":"hand_L","CTRL_HAND.R":"hand_R","IK_FOOT.L":"IK_foot_L","IK_FOOT.R":"IK_foot_R","POLE_KNEE.L":"POLE_knee_L","POLE_KNEE.R":"POLE_knee_R","CTRL_EYE_TARGET":"eye_aim"}
    arm["control_aliases"]=aliases

def beauty_touchups(arm):
    white=mat("eye_highlight",(1,1,.94),.15,1.0)
    for s,side in ((1,"L"),(-1,"R")):
        h=ell("KIKO_GEO_eye_highlight_"+side,(s*.165,-.558,2.365),(.030,.010,.040),white,12)
        w=h.matrix_world.copy(); h.parent=arm; h.parent_type="BONE"; h.parent_bone="head"; h.matrix_world=w

def environment():
    # Remove neutral studio while preserving KIKO.
    for o in list(bpy.data.objects):
        if o.name.startswith("STUDIO_") or o.name in {"Key","Fill","Rim"}: bpy.data.objects.remove(o,do_unlink=True)
    ground=mat("jungle_ground",(.075,.16,.07),.95); bark=mat("jungle_bark",(.13,.055,.018),.95); leaf=mat("jungle_leaf",(.06,.29,.10),.88); leaf2=mat("jungle_leaf_warm",(.20,.43,.09),.9)
    cube("JUNGLE_ground",(0,1,-.18),(10,8,.18),ground,.12)
    for i,(x,y,s) in enumerate([(-4,2,1.2),(4,2,1.15),(-5,5,1.5),(5,5,1.4),(-3,7,1.6),(3,7,1.7)]):
        bpy.ops.mesh.primitive_cylinder_add(vertices=12,radius=.34*s,depth=5*s,location=(x,y,2.2*s)); t=bpy.context.object; t.name=f"TREE_{i}"; t.data.materials.append(bark); smooth(t)
        for j in range(4): ell(f"CANOPY_{i}_{j}",(x+(j-1.5)*.55*s,y,4.4*s+(j%2)*.35),(.95*s,.75*s,.72*s),leaf if j%2 else leaf2)
    # Foreground bushes and warm flowers create depth without heavy assets.
    for i in range(20):
        x=-5.5+(i%10)*1.2; y=.8+(i//10)*5.8; z=.15
        ell(f"BUSH_{i}",(x,y,z),(.65,.42,.45),leaf if i%2 else leaf2)
    for i in range(8):
        c=mat(f"flower_{i}",(.95,.20+.05*(i%3),.04),.7,0.08); ell(f"FLOWER_{i}",(-3.8+i*1.05,1.0,.22),(.08,.08,.13),c)
    world=bpy.context.scene.world; world.color=(.025,.045,.025)
    sun_data=bpy.data.lights.new("JUNGLE_sun","SUN"); sun_data.energy=2.35; sun_data.color=(1,.60,.34); sun=bpy.data.objects.new("JUNGLE_sun",sun_data); bpy.context.collection.objects.link(sun); sun.rotation_euler=(math.radians(28),math.radians(-20),math.radians(-35))
    fill_data=bpy.data.lights.new("JUNGLE_fill","AREA"); fill_data.energy=1000; fill_data.color=(.34,.60,1); fill_data.shape="DISK"; fill_data.size=6; fill=bpy.data.objects.new("JUNGLE_fill",fill_data); bpy.context.collection.objects.link(fill); fill.location=(-3,-3,5); fill.rotation_euler=((Vector((0,1,1))-fill.location).to_track_quat("-Z","Y").to_euler())
    rim_data=bpy.data.lights.new("KIKO_tail_rim","AREA"); rim_data.energy=650; rim_data.color=(1,.32,.10); rim_data.shape="DISK"; rim_data.size=4; rim=bpy.data.objects.new("KIKO_tail_rim",rim_data); bpy.context.collection.objects.link(rim); rim.location=(3,3,3); rim.rotation_euler=((Vector((0,0,1.2))-rim.location).to_track_quat("-Z","Y").to_euler())

def props():
    orange=mat("runaway_fruit",(.95,.24,.025),.55); green=mat("fruit_leaf",(.12,.42,.08),.8); dark=mat("creature_dark",(.055,.035,.025),.75); cream=mat("creature_cream",(.78,.61,.36),.85); black=mat("creature_eye",(.01,.006,.004),.25)
    def parent_keep(child,parent):
        w=child.matrix_world.copy(); child.parent=parent; child.matrix_world=w
    fruit=ell("PROP_runaway_fruit",(0,-.25,.20),(.28,.25,.30),orange); leaf=ell("PROP_fruit_leaf",(.10,-.25,.47),(.16,.05,.07),green); leaf.rotation_euler=(0,.3,.5); parent_keep(leaf,fruit)
    creature=ell("CREATURE_body",(2.0,.08,.24),(.27,.22,.25),dark); parent_keep(ell("CREATURE_belly",(2.0,-.13,.22),(.16,.04,.15),cream),creature)
    for s in (-1,1):
        parent_keep(ell("CREATURE_ear"+str(s),(2.0+s*.18,.02,.47),(.10,.07,.16),dark),creature)
        parent_keep(ell("CREATURE_eye"+str(s),(2.0+s*.085,-.205,.31),(.028,.018,.04),black),creature)
    return fruit,creature

def animate(arm,fruit,creature,cam):
    sc=bpy.context.scene; sc.frame_start=1; sc.frame_end=360; sc.render.fps=12
    arm.animation_data_clear(); arm.animation_data_create(); arm.animation_data.action=bpy.data.actions.new("KIKO_ACT_runaway_fruit_30s")
    # KIKO progression: entrance, discovery, pursuit, reveal, friendly settle.
    for f,p in [(1,(-2.5,0,0)),(60,(-1.1,0,0)),(120,(-.7,0,0)),(168,(-.4,0,0)),(240,(1.0,0,0)),(300,(1.0,0,0)),(360,(1.0,0,0))]: key_obj(arm,f,loc=p)
    for f,a in [(1,0),(15,.45),(30,0),(45,-.45),(60,0),(168,0),(184,.55),(200,0),(216,-.55),(232,0),(240,0)]:
        key_bone(arm,"thigh_L",f,(a,0,0)); key_bone(arm,"thigh_R",f,(-a,0,0)); key_bone(arm,"upperarm_L",f,(-a*.55,0,0)); key_bone(arm,"upperarm_R",f,(a*.55,0,0))
    for f,r in [(1,0),(60,0),(78,-.22),(96,.18),(120,0),(132,-.30),(168,-.15),(240,.15),(264,-.28),(300,.12),(330,-.10),(360,0)]: key_bone(arm,"head",f,(0,0,r))
    # Discovery anticipation, surprise, then friendly wave.
    for f,z in [(1,0),(72,0),(92,.07),(112,0),(120,.11),(132,0),(240,0),(258,.12),(276,0),(300,0),(330,.03),(360,0)]: key_bone(arm,"spine_02",f,(z,0,0))
    for f,r1,r2 in [(300,0,0),(312,-1.45,-.9),(324,-1.30,-.45),(338,-1.45,-.9),(350,-1.3,-.45),(360,0,0)]: key_bone(arm,"upperarm_L",f,(0,r1*.12,r1)); key_bone(arm,"lowerarm_L",f,(0,r2,0))
    for i in range(1,7):
        for f,a in [(1,0),(120,0),(132+i*2,.17+i*.02),(154+i*2,-.08),(240,0),(258+i*2,.20),(286+i*2,-.07),(360,0)]: key_bone(arm,f"tail_{i:02d}",f,(a,0,((-1)**i)*a*.30))
    # Fruit rolls away, pauses beside hidden creature.
    for f,p,r in [(1,(0,-.25,.20),0),(120,(0,-.25,.20),0),(132,(.35,-.20,.22),2),(150,(1.1,-.10,.21),7),(168,(2.0,.02,.21),12),(240,(2.25,.02,.21),14),(360,(2.25,.02,.21),14)]: key_obj(fruit,f,loc=p,rot=(0,r,0))
    creature.scale=(.001,.001,.001); creature.keyframe_insert("scale",frame=1); creature.keyframe_insert("scale",frame=238); creature.scale=(1,1,1); creature.keyframe_insert("scale",frame=252)
    for f,r in [(252,0),(264,-.15),(280,.15),(300,0),(360,0)]: key_obj(creature,f,rot=(0,0,r))
    # Six shots; near-constant endpoints make deliberate cuts with tiny pushes.
    shots=[(1,(-4.3,-8.3,2.25),(-1.25,0,1.40)),(61,(-.6,-7.2,1.85),(-.55,0,1.35)),(121,(2.2,-6.6,1.45),(.85,0,.92)),(169,(-1.2,-7.6,1.85),(.65,0,1.30)),(241,(4.5,-6.8,1.55),(1.55,0,1.00)),(301,(2.6,-7.2,1.95),(1.15,0,1.42))]
    for idx,(f,loc,target) in enumerate(shots):
        end=(shots[idx+1][0]-1) if idx+1<len(shots) else 360
        for hold in (f,end):
            cam.location=loc; cam.rotation_euler=(Vector(target)-cam.location).to_track_quat("-Z","Y").to_euler(); cam.data.lens=56 if idx not in {1,4} else 60; cam.keyframe_insert("location",frame=hold); cam.keyframe_insert("rotation_euler",frame=hold); cam.data.keyframe_insert("lens",frame=hold)
    # Blender 5.x layered actions no longer expose legacy action.fcurves here;
    # default Bezier interpolation gives each shot a gentle cinematic push.

def main():
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/"KIKO_master_v1_1.blend"))
    arm=bpy.data.objects["KIKO_RIG_armature"]; add_alias_controls(arm); beauty_touchups(arm); environment(); fruit,creature=props(); cam=bpy.data.objects["KIKO_CAM"]; animate(arm,fruit,creature,cam)
    sc=bpy.context.scene; sc.frame_start=int(os.environ.get("KIKO_RENDER_START","1")); sc.render.engine="BLENDER_EEVEE"; sc.render.resolution_x=960; sc.render.resolution_y=540; sc.render.resolution_percentage=100; sc.render.image_settings.file_format="PNG"; sc.render.image_settings.color_mode="RGB"; sc.render.film_transparent=False
    FRAMES.mkdir(parents=True,exist_ok=True); sc.render.filepath=str(FRAMES/"frame_"); OUT.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/"KIKO_runaway_fruit_v001.blend")); bpy.ops.render.render(animation=True); bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/"KIKO_runaway_fruit_v001.blend"))
if __name__=="__main__": main()
