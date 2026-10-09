#!/usr/bin/env python3
"""Reference-led KIKO visual rebuild; retains only the approved rig architecture."""
from pathlib import Path
import math, json
import bpy
from mathutils import Vector

BLENDER_DIR=Path(__file__).resolve().parent; ROOT=BLENDER_DIR.parent; REVIEW=ROOT/"review"/"kiko_rebuild"; MASTER=BLENDER_DIR/"KIKO_master_rebuild_v001.blend"

def mat(name,c,rough=.88,metal=0):
    m=bpy.data.materials.get(name) or bpy.data.materials.new(name); m.diffuse_color=(*c,1); m.use_nodes=True
    p=m.node_tree.nodes.get("Principled BSDF"); p.inputs["Base Color"].default_value=(*c,1); p.inputs["Roughness"].default_value=rough; p.inputs["Metallic"].default_value=metal
    return m

def smooth(o,sub=1,bev=0):
    if o.type=="MESH":
        for p in o.data.polygons:p.use_smooth=True
    if bev:
        b=o.modifiers.new("handcrafted edge","BEVEL"); b.width=bev; b.segments=3
    if sub:
        s=o.modifiers.new("organic subdivision","SUBSURF"); s.levels=1; s.render_levels=sub
    return o

def ell(name,loc,scale,ma,seg=24,rings=16):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg,ring_count=rings,location=loc); o=bpy.context.object; o.name=name; o.scale=scale; bpy.ops.object.transform_apply(location=False,rotation=False,scale=True); o.data.materials.append(ma); return smooth(o,1)

def loft(name,centers,radii,ma,sides=18):
    vs=[]; fs=[]
    for i,(c,(rx,rd)) in enumerate(zip(centers,radii)):
        prev=Vector(centers[max(0,i-1)]); nxt=Vector(centers[min(len(centers)-1,i+1)]); tangent=(nxt-prev).normalized(); lateral=Vector((1,0,0)); depth=tangent.cross(lateral).normalized()
        for j in range(sides):
            a=math.tau*j/sides; vs.append(Vector(c)+lateral*math.cos(a)*rx+depth*math.sin(a)*rd)
    for i in range(len(centers)-1):
        for j in range(sides):a=i*sides+j;b=i*sides+(j+1)%sides;fs.append((a,b,b+sides,a+sides))
    me=bpy.data.meshes.new(name+"_mesh"); me.from_pydata(vs,[],fs); me.materials.append(ma); o=bpy.data.objects.new(name,me); bpy.context.collection.objects.link(o); return smooth(o,1)

def leaf_ear(name,s,outer,inner):
    # Low, broad asymmetrical leaf -- deliberately horizontal rather than rabbit-like.
    pts=[(-.02,.02),(.15,-.08),(.40,-.10),(.70,-.05),(.92,.08),(1.04,.20),(.90,.32),(.62,.38),(.34,.36),(.12,.28),(-.02,.18),(-.08,.09)]
    base=Vector((s*.31,-.01,2.30)); front=[]
    for x,z in pts:front.append((base.x+s*x,base.y-.055,base.z+z))
    back=[(x,y+.12,z) for x,y,z in front]; vs=front+back; fs=[tuple(range(12)),tuple(reversed(range(12,24)))]
    for i in range(12):fs.append((i,(i+1)%12,(i+1)%12+12,i+12))
    me=bpy.data.meshes.new(name+"_mesh"); me.from_pydata(vs,[],fs); me.materials.append(outer); o=bpy.data.objects.new(name,me); bpy.context.collection.objects.link(o); smooth(o,1,.035)
    inn=[(base.x+(x-base.x)*.80,y-.012,base.z+(z-base.z)*.66+.045) for x,y,z in front]; mi=bpy.data.meshes.new(name+"_inner_mesh"); mi.from_pydata(inn,[],[tuple(range(12))]); mi.materials.append(inner); io=bpy.data.objects.new(name+"_inner",mi); bpy.context.collection.objects.link(io); smooth(io,1,.018)
    return o,io

def curve(name,pts,r,ma,cyclic=False):
    cu=bpy.data.curves.new(name+"_curve","CURVE"); cu.dimensions="3D"; cu.bevel_depth=r; cu.bevel_resolution=3
    sp=cu.splines.new("BEZIER"); sp.bezier_points.add(len(pts)-1)
    for b,p in zip(sp.bezier_points,pts):b.co=p;b.handle_left_type=b.handle_right_type="AUTO"
    sp.use_cyclic_u=cyclic; o=bpy.data.objects.new(name,cu); bpy.context.collection.objects.link(o); cu.materials.append(ma); return o

def cube(name,loc,scale,ma,bev=.06):
    bpy.ops.mesh.primitive_cube_add(location=loc); o=bpy.context.object;o.name=name;o.scale=scale;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(ma);return smooth(o,0,bev)

def bind(obj,arm,bones):
    if obj.type!="MESH":return
    mod=obj.modifiers.new("KIKO rebuild armature","ARMATURE");mod.object=arm;mod.use_deform_preserve_volume=True
    valid=[arm.data.bones[n] for n in bones if n in arm.data.bones]; groups={b.name:obj.vertex_groups.new(name=b.name) for b in valid}
    for v in obj.data.vertices:
        p=obj.matrix_world@v.co; ranked=sorted(((p-(arm.matrix_world@((b.head_local+b.tail_local)*.5))).length,b.name,b) for b in valid)[:2]; inv=[1/max(x[0],.035)**2 for x in ranked]; total=sum(inv)
        for w,(_,_,b) in zip(inv,ranked):groups[b.name].add([v.index],w/total,"REPLACE")
    obj.parent=arm

def bone_parent(o,arm,bone):
    w=o.matrix_world.copy();o.parent=arm;o.parent_type="BONE";o.parent_bone=bone;o.matrix_world=w

def build(arm):
    m={"teal":mat("rebuild_fur_teal",(.055,.235,.245),.96),"cream":mat("rebuild_fur_cream",(.80,.70,.54),.97),"rust":mat("rebuild_fur_rust",(.66,.18,.055),.94),"inner":mat("rebuild_inner_ear",(.90,.35,.24),.90),"iris":mat("rebuild_amber_iris",(.58,.18,.025),.45),"pupil":mat("rebuild_pupil",(.012,.007,.004),.30),"nose":mat("rebuild_pink_nose",(.67,.23,.20),.68),"mouth":mat("rebuild_mouth",(.18,.035,.025),.75),"scarf":mat("rebuild_scarf",(.62,.14,.045),.94),"cloth":mat("rebuild_cloth",(.10,.17,.15),.97),"leather":mat("rebuild_leather",(.16,.065,.025),.93),"brass":mat("rebuild_brass",(.58,.30,.055),.40,.55)}
    deform=[]
    body=loft("REBUILD_body",[(0,0,.70),(0,.02,.91),(0,.03,1.19),(0,.01,1.45),(0,0,1.61)],[(.28,.22),(.40,.31),(.43,.33),(.39,.29),(.25,.20)],m["teal"],22);deform.append((body,["pelvis","spine_01","spine_02","chest","neck"]))
    head=loft("REBUILD_head",[(0,0,1.68),(0,-.01,1.88),(0,.01,2.10),(0,.035,2.31),(0,.04,2.48)],[(.22,.19),(.35,.30),(.51,.39),(.49,.36),(.32,.24)],m["teal"],24);deform.append((head,["head","neck"]))
    # Integrated cream facial mask: central muzzle plus overlapping fluffy cheek lobes.
    # Broad cream facial mask sits close to the skull so the eyes and muzzle read as
    # one feline plane rather than a collection of white toy balls.
    mask=ell("REBUILD_face_mask",(0,-.292,2.13),(.375,.075,.315),m["cream"]);deform.append((mask,["head"]))
    # Two integrated muzzle pads plus scalloped cheek masses; no whisker-bar silhouette.
    for s,side in ((1,"L"),(-1,"R")):
        pad=ell("REBUILD_muzzle_pad_"+side,(s*.080,-.405,2.015),(.160,.115,.125),m["cream"]);deform.append((pad,["head"]))
    for s,side in ((1,"L"),(-1,"R")):
        cheek=ell("REBUILD_cheek_"+side,(s*.285,-.300,1.995),(.205,.078,.155),m["cream"]);deform.append((cheek,["head"]))
        for j,(x,z,sc) in enumerate(((.43,2.09,.09),(.48,2.00,.105),(.43,1.91,.08))):
            tuft=loft(f"REBUILD_cheek_tuft_{side}_{j}",[(s*(x-.05),-.27,z),(s*(x+.10),-.245,z-.015)],[(sc,.055),(.012,.009)],m["cream"],10);deform.append((tuft,["head"]))
        ear,inner=leaf_ear("REBUILD_ear_"+side,s,m["teal"],m["inner"]);deform += [(ear,["ear_01_"+side,"ear_02_"+side,"ear_03_"+side]),(inner,["ear_01_"+side,"ear_02_"+side,"ear_03_"+side])]
        # Reference speckles.
        for i,(dx,dz) in enumerate(((.32,.15),(.43,.24),(.24,.28),(.52,.12))):
            sp=ell(f"REBUILD_ear_spot_{side}_{i}",(s*(.38+dx*1.35),-.075,2.28+dz*.65),(.025,.009,.018),m["rust"],12,8);bone_parent(sp,arm,"ear_02_"+side)
        eye=ell("REBUILD_eye_"+side,(s*.165,-.350,2.255),(.155,.105,.180),m["cream"]);deform.append((eye,["head"]))
        iris=ell("REBUILD_iris_"+side,(s*.165,-.450,2.25),(.090,.018,.105),m["iris"],20,12);deform.append((iris,["head"]))
        pupil=ell("REBUILD_pupil_"+side,(s*.165,-.468,2.25),(.041,.010,.066),m["pupil"],16,10);deform.append((pupil,["head"]))
        curve("REBUILD_lid_"+side,[(s*.30,-.466,2.31),(s*.165,-.485,2.40),(s*.03,-.466,2.32)],.020,m["teal"])
        curve("REBUILD_brow_"+side,[(s*.30,-.40,2.43),(s*.17,-.43,2.48),(s*.04,-.40,2.44)],.021,m["teal"])
    nose=ell("REBUILD_nose",(0,-.532,2.08),(.060,.034,.043),m["nose"],18,10);deform.append((nose,["head"]))
    curve("REBUILD_mouth",[(-.11,-.555,1.97),(0,-.57,1.94),(.11,-.555,1.97)],.018,m["mouth"])
    # Layered swept crest locks with curved roots and irregular overlap.
    for i,(x,z,lean,h,w) in enumerate([(-.30,2.42,-.24,.27,.13),(-.22,2.47,-.30,.39,.15),(-.12,2.49,-.32,.51,.17),(-.01,2.50,-.28,.58,.18),(.10,2.48,-.20,.50,.17),(.20,2.45,-.12,.39,.15),(.29,2.42,-.04,.27,.13)]):
        tuft=loft(f"REBUILD_crest_{i}",[(x,.03,z),(x+lean*.18,.015,z+h*.38),(x+lean*.55,.005,z+h*.75),(x+lean,.00,z+h)],[(w,.105),(w*.92,.090),(w*.58,.052),(.018,.014)],m["cream" if i in (2,5) else "teal"],14);deform.append((tuft,["head"]))
    # Layered cream bib breaks the smooth torso silhouette at camera distance.
    bib=loft("REBUILD_chest_bib",[(0,-.285,1.47),(0,-.325,1.28),(0,-.335,1.08),(0,-.30,.91)],[(.23,.035),(.29,.045),(.25,.045),(.08,.025)],m["cream"],18);deform.append((bib,["chest","spine_02","spine_01"]))
    for i,(x,z) in enumerate(((-.23,1.29),(.23,1.29),(-.20,1.11),(.20,1.11),(0,.94))):
        tip=loft(f"REBUILD_chest_tuft_{i}",[(x,-.345,z),(x*1.15,-.355,z-.15)],[(.09,.035),(.012,.008)],m["cream"],10);deform.append((tip,["chest","spine_02"]))
    # Soft tapered limbs and articulated paws.
    for s,side in ((1,"L"),(-1,"R")):
        a=loft("REBUILD_arm_"+side,[(s*.31,0,1.52),(s*.43,-.015,1.35),(s*.51,-.025,1.12),(s*.55,-.04,.91)],[(.16,.15),(.15,.14),(.13,.12),(.105,.095)],m["teal"],16);deform.append((a,["upperarm_"+side,"lowerarm_"+side,"hand_"+side]))
        palm=loft("REBUILD_paw_"+side,[(s*.55,-.04,.91),(s*.57,-.08,.79),(s*.57,-.14,.68)],[(.10,.09),(.18,.15),(.14,.11)],m["teal"],14);deform.append((palm,["hand_"+side]))
        for i in range(4):
            d=ell(f"REBUILD_finger_{i}_{side}",(s*(.49+i*.052),-.22,.68+i*.004),(.036,.075,.045),m["cream"],12,8);deform.append((d,["hand_"+side]))
        leg=loft("REBUILD_leg_"+side,[(s*.18,0,.86),(s*.19,.01,.62),(s*.20,0,.38),(s*.20,-.015,.16)],[(.18,.17),(.16,.15),(.14,.13),(.115,.105)],m["teal"],16);deform.append((leg,["thigh_"+side,"shin_"+side,"foot_"+side]))
        foot=loft("REBUILD_foot_"+side,[(s*.20,.02,.17),(s*.20,-.18,.12),(s*.20,-.40,.09)],[(.13,.10),(.18,.12),(.21,.09)],m["teal"],16);deform.append((foot,["foot_"+side]))
        for i in range(4):
            toe=ell(f"REBUILD_toe_{i}_{side}",(s*(.09+i*.072),-.47,.085),(.045,.075,.042),m["cream"],12,8);deform.append((toe,["foot_"+side]))
    centers=[(0,.10,.87),(0,.30,.66),(0,.54,.58),(0,.78,.64),(0,1.02,.80),(0,1.22,1.02),(0,1.34,1.24),(0,1.37,1.40)]
    tail=loft("REBUILD_tail_plume",centers,[(.20,.18),(.29,.26),(.34,.30),(.34,.30),(.30,.26),(.24,.21),(.16,.14),(.025,.02)],m["teal"],22);tail.data.materials.append(m["cream"]);tail.data.materials.append(m["rust"])
    for p in tail.data.polygons:
        y=sum(tail.data.vertices[i].co.y for i in p.vertices)/len(p.vertices);p.material_index=1 if .56<y<.78 or 1.12<y<1.28 else (2 if .86<y<1.08 or y>1.28 else 0)
    deform.append((tail,[f"tail_{i:02d}" for i in range(1,7)]))
    # Layered explorer costume, intentionally worn and asymmetric.
    vest=loft("REBUILD_vest",[(0,-.005,.88),(0,-.005,1.15),(0,-.005,1.48)],[(.35,.285),(.40,.305),(.34,.27)],m["cloth"],20);deform.append((vest,["pelvis","spine_01","spine_02","chest"]))
    curve("REBUILD_scarf",[(-.25,-.02,1.65),(0,-.24,1.60),(.25,-.02,1.65),(0,.18,1.67)],.075,m["scarf"],True)
    curve("REBUILD_belt",[(-.34,0,.98),(0,-.28,.96),(.34,0,.98),(0,.24,.99)],.042,m["leather"],True)
    for s,side in ((1,"L"),(-1,"R")):curve("REBUILD_harness_"+side,[(s*.25,-.27,1.46),(s*.07,-.31,1.02)],.026,m["leather"])
    pack=cube("REBUILD_backpack",(0,.31,1.26),(.27,.17,.33),m["leather"],.09);bone_parent(pack,arm,"chest")
    bed=curve("REBUILD_bedroll",[(-.24,.48,1.53),(.24,.48,1.53)],.105,m["scarf"]);bone_parent(bed,arm,"chest")
    charm=ell("REBUILD_compass",(.12,-.34,.98),(.065,.022,.065),m["brass"],18,10);bone_parent(charm,arm,"pelvis")
    # Bind deforming meshes; rigid curves follow the nearest semantic bone.
    for o,bones in deform:bind(o,arm,bones)
    for o in bpy.data.objects:
        if o.name.startswith("REBUILD_") and o.parent is None:bone_parent(o,arm,"head" if any(x in o.name for x in ("lid","brow","mouth")) else "chest")
    return m

def studio():
    bg=mat("rebuild_studio",(.075,.085,.095),.9);cube("REBUILD_floor",(0,0,-.10),(5,5,.08),bg,.02)
    bpy.context.scene.world.color=(.025,.03,.035)
    for name,loc,e,size,c in [("REBUILD_key",(-3,-4,5),900,5,(1,.78,.62)),("REBUILD_fill",(4,-3,3.5),650,5,(.50,.68,1)),("REBUILD_rim",(2,3,4),600,4,(1,.40,.16))]:
        d=bpy.data.lights.new(name,"AREA");d.energy=e;d.size=size;d.shape="DISK";d.color=c;o=bpy.data.objects.new(name,d);bpy.context.collection.objects.link(o);o.location=loc;o.rotation_euler=(Vector((0,0,1.4))-o.location).to_track_quat("-Z","Y").to_euler()
    d=bpy.data.cameras.new("REBUILD_CAM_data");cam=bpy.data.objects.new("REBUILD_CAM",d);bpy.context.collection.objects.link(cam);bpy.context.scene.camera=cam;return cam

def render(cam):
    REVIEW.mkdir(parents=True,exist_ok=True);sc=bpy.context.scene;sc.render.engine="BLENDER_EEVEE";sc.render.resolution_x=700;sc.render.resolution_y=700;sc.render.resolution_percentage=100;sc.render.image_settings.file_format="PNG";sc.view_settings.look="AgX - Medium High Contrast";sc.frame_set(1)
    views=[("front",(0,-6.2,1.60),(0,0,1.45),64),("three_quarter",(4.0,-5.1,1.72),(0,0,1.47),64),("side",(6.2,0,1.60),(0,0,1.45),66),("back",(0,6.2,1.60),(0,0,1.45),64),("face_closeup",(0,-4.0,2.28),(0,0,2.20),76)]
    for n,loc,target,lens in views:cam.location=loc;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat("-Z","Y").to_euler();cam.data.lens=lens;sc.render.filepath=str(REVIEW/(n+".png"));bpy.ops.render.render(write_still=True)

def main():
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/"KIKO_master_v1_1.blend"));arm=bpy.data.objects["KIKO_RIG_armature"]
    for o in list(bpy.data.objects):
        if o!=arm:bpy.data.objects.remove(o,do_unlink=True)
    arm.animation_data_clear();arm["kiko_asset_version"]="reference-rebuild-v001";arm["reference_sheet"]="assets/hero/kiko.png"
    build(arm);cam=studio();bpy.ops.wm.save_as_mainfile(filepath=str(MASTER));render(cam);bpy.ops.wm.save_as_mainfile(filepath=str(MASTER))
    (REVIEW/"build_report.json").write_text(json.dumps({"reference":"assets/hero/kiko.png","armature":arm.name,"rig_rebuilt":False,"stage":"beauty_gate_A","vertices":sum(len(o.data.vertices) for o in bpy.data.objects if o.type=="MESH"),"polygons":sum(len(o.data.polygons) for o in bpy.data.objects if o.type=="MESH")},indent=2))
if __name__=="__main__":main()
