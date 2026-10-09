#!/usr/bin/env python3
"""KIKO V1.2 art-direction pass. Visible meshes only; rig is preserved."""
from __future__ import annotations
import json, math
from pathlib import Path
import bpy
from mathutils import Vector

BLENDER_DIR=Path(__file__).resolve().parent; ROOT=BLENDER_DIR.parent; REVIEW=ROOT/"review"/"kiko_v1_2"; MASTER=BLENDER_DIR/"KIKO_master_v1_2.blend"

def scale_mesh(o,sx=1,sy=1,sz=1):
    for v in o.data.vertices: v.co.x*=sx; v.co.y*=sy; v.co.z*=sz

def shape_head():
    head=bpy.data.objects["KIKO_GEO_head"]
    for v in head.data.vertices:
        z=v.co.z
        # Flatten cranial roundness, retain wide cheeks, narrow the jaw.
        if z<1.90: sx=.82
        elif z<2.17: sx=1.075
        elif z<2.43: sx=1.015
        else: sx=.95
        v.co.x*=sx
        if z>2.42: v.co.z=2.42+(z-2.42)*.91
    muzzle=bpy.data.objects["KIKO_GEO_muzzle"]; scale_mesh(muzzle,.94,.74,.88); muzzle.location.y+=.045
    nose=bpy.data.objects["KIKO_GEO_nose"]; scale_mesh(nose,.78,.72,.78); nose.location.y+=.045
    # Make cheek ruffs broader, layered and less whisker-like.
    for side,s in (("L",1),("R",-1)):
        cheek=bpy.data.objects["KIKO_GEO_cheek_fluff_"+side]; anchor=s*.28
        for v in cheek.data.vertices:
            v.co.x=anchor+(v.co.x-anchor)*1.16
            v.co.z=2.06+(v.co.z-2.06)*1.10
            v.co.y=-.24+(v.co.y+.24)*1.10

def shape_ears_eyes():
    for side,s in (("L",1),("R",-1)):
        # V1.1 ears become 18% lower and slightly narrower, improving aspect ratio.
        for prefix in ("KIKO_GEO_ear_","KIKO_GEO_ear_inner_"):
            o=bpy.data.objects[prefix+side]; ax=s*.32; az=2.48
            for v in o.data.vertices:
                dx=v.co.x-ax; dz=v.co.z-az
                v.co.x=ax+dx*.93+s*dz*.05
                v.co.z=az+dz*.82
                v.co.y*=1.08
        eye=bpy.data.objects["KIKO_GEO_eye_"+side]; scale_mesh(eye,.94,1,.69); eye.location.x+=s*.022
        iris=bpy.data.objects["KIKO_GEO_iris_"+side]; scale_mesh(iris,1.06,1,.86); iris.location.x+=s*.022
        pupil=bpy.data.objects["KIKO_GEO_pupil_"+side]; scale_mesh(pupil,1.12,1,.90); pupil.location.x+=s*.022
        lid=bpy.data.objects.get("KIKO_GEO_lid_"+side)
        if lid and lid.type=="CURVE": lid.data.bevel_depth=.034

def shape_body_limbs():
    body=bpy.data.objects["KIKO_GEO_body"]
    for v in body.data.vertices:
        z=v.co.z; factor=1.14 if 1.05<z<1.55 else 1.09
        v.co.x*=factor; v.co.y*=1.10
    for side,s in (("L",1),("R",-1)):
        arm=bpy.data.objects["KIKO_GEO_arm_"+side]
        for v in arm.data.vertices:
            center=s*(.31+(1.52-v.co.z)*.38); v.co.x=center+(v.co.x-center)*1.12
        leg=bpy.data.objects["KIKO_GEO_leg_"+side]
        for v in leg.data.vertices:
            center=s*.20; v.co.x=center+(v.co.x-center)*1.12; v.co.y*=1.08
        hand=bpy.data.objects["KIKO_GEO_hand_"+side]
        center=Vector((s*.57,-.09,.78))
        for v in hand.data.vertices: v.co=center+(v.co-center)*Vector((1.12,1.10,1.06))
        foot=bpy.data.objects["KIKO_GEO_foot_"+side]
        center=Vector((s*.20,-.20,.12))
        for v in foot.data.vertices: v.co=center+(v.co-center)*Vector((1.12,1.13,1.04))
        for i in range(4):
            d=bpy.data.objects.get(f"KIKO_GEO_digit_{i}_{side}")
            if d: scale_mesh(d,1.10,1.08,1.06)
        for i in range(3):
            t=bpy.data.objects.get(f"KIKO_GEO_toe_{i}_{side}")
            if t: scale_mesh(t,1.12,1.10,1.06)
    tail=bpy.data.objects["KIKO_GEO_tail_plume"]
    for v in tail.data.vertices:
        # Preserve root and increase fullness progressively through the plume.
        factor=1.0+max(0,min(1,(v.co.y-.18)/.65))*.18
        v.co.x*=factor
        if v.co.y>.32: v.co.z=.83+(v.co.z-.83)*1.09

def soften_crest():
    for i in range(5):
        o=bpy.data.objects.get(f"KIKO_GEO_crest_{i}")
        if not o: continue
        # Broader, lower, overlapping fur leaves rather than vertical spikes.
        xs=[-.18,0,.18,-.31,.31][i]; zs=[2.66,2.78,2.66,2.60,2.60][i]; c=Vector((xs,.02,zs))
        for v in o.data.vertices: v.co=c+(v.co-c)*Vector((1.28,1.05,.68))

def face_accents():
    arm=bpy.data.objects["KIKO_RIG_armature"]; orange=bpy.data.materials["fur_orange"]; gray=bpy.data.materials["fur_gray"]
    def tube(name,points,radius,material):
        cu=bpy.data.curves.new(name+"_curve","CURVE"); cu.dimensions="3D"; cu.bevel_depth=radius; cu.bevel_resolution=3; cu.resolution_u=8
        sp=cu.splines.new("BEZIER"); sp.bezier_points.add(len(points)-1)
        for b,p in zip(sp.bezier_points,points): b.co=p; b.handle_left_type=b.handle_right_type="AUTO"
        o=bpy.data.objects.new(name,cu); bpy.context.collection.objects.link(o); cu.materials.append(material)
        w=o.matrix_world.copy(); o.parent=arm; o.parent_type="BONE"; o.parent_bone="head"; o.matrix_world=w
    # Clear graphic brow and upper-lid framing, close to the eyes rather than floating.
    for s,side in ((1,"L"),(-1,"R")):
        tube("KIKO_V12_brow_"+side,[(s*.34,-.49,2.47),(s*.21,-.53,2.51),(s*.09,-.50,2.48)],.026,orange)
        tube("KIKO_V12_upper_lid_"+side,[(s*.34,-.548,2.34),(s*.21,-.57,2.40),(s*.08,-.548,2.34)],.020,gray)
    # Convert single whisker wedges into shorter layered cheek-fur fans.
    for side,s in (("L",1),("R",-1)):
        cheek=bpy.data.objects["KIKO_GEO_cheek_fluff_"+side]; anchor=s*.28
        for v in cheek.data.vertices:v.co.x=anchor+(v.co.x-anchor)*.72
        fur_clump("KIKO_V12_cheek_mid_"+side,(s*.39,-.28,2.13),s,"head",bpy.data.materials["fur_cream"],(.78,.92,.72))
        fur_clump("KIKO_V12_cheek_low_"+side,(s*.37,-.25,2.04),s,"head",bpy.data.materials["fur_cream"],(.66,.85,.62))
    # Round the angular ear perimeter and reduce the remaining rabbit-like height.
    for side,s in (("L",1),("R",-1)):
        for prefix in ("KIKO_GEO_ear_","KIKO_GEO_ear_inner_"):
            o=bpy.data.objects[prefix+side]; ax=s*.32; az=2.48
            for v in o.data.vertices:
                v.co.x=ax+(v.co.x-ax)*.92; v.co.z=az+(v.co.z-az)*.86
            bevel=o.modifiers.get("V1.2 soft ear edge") or o.modifiers.new("V1.2 soft ear edge","BEVEL"); bevel.width=.055 if "inner" not in prefix else .025; bevel.segments=4

def fur_clump(name,loc,side,bone,material,scale=(1,1,1)):
    # Small custom leaf/wedge topology, rigidly bone-parented for stable overlap.
    s=side; x,y,z=loc
    verts=[(x,y,z+.10),(x+s*.11,y-.015,z+.025),(x+s*.15,y,z-.07),(x,y+.025,z-.02),(x-s*.04,y,z+.025),
           (x,y+.06,z+.08),(x+s*.09,y+.05,z+.02),(x+s*.12,y+.055,z-.05),(x,y+.07,z-.01),(x-s*.03,y+.055,z+.02)]
    faces=[(0,1,2,3,4),(9,8,7,6,5),(0,5,6,1),(1,6,7,2),(2,7,8,3),(3,8,9,4),(4,9,5,0)]
    me=bpy.data.meshes.new(name+"_mesh"); me.from_pydata(verts,[],faces); me.materials.append(material)
    o=bpy.data.objects.new(name,me); bpy.context.collection.objects.link(o); o.scale=scale
    for p in me.polygons:p.use_smooth=True
    arm=bpy.data.objects["KIKO_RIG_armature"]; w=o.matrix_world.copy(); o.parent=arm; o.parent_type="BONE"; o.parent_bone=bone; o.matrix_world=w

def modeled_fur_accents():
    gray=bpy.data.materials["fur_gray"]
    for side,s in (("L",1),("R",-1)):
        fur_clump("KIKO_V12_forearm_tuft_"+side,(s*.56,-.05,.99),s,"lowerarm_"+side,gray,(1.0,1.0,1.0))
        fur_clump("KIKO_V12_leg_tuft_"+side,(s*.21,-.01,.31),s,"shin_"+side,gray,(.88,.9,.84))

def final_beauty_refinement():
    # Final gate: add compact heroic torso mass without changing bones/weights.
    body=bpy.data.objects["KIKO_GEO_body"]
    for v in body.data.vertices:
        if .86<v.co.z<1.62:
            v.co.x*=1.12
            v.co.y*=1.10
    # Fuller integrated muzzle and rounder cheek layers.
    muzzle=bpy.data.objects["KIKO_GEO_muzzle"]; scale_mesh(muzzle,1.08,1.035,1.055); muzzle.location.y+=.008
    for side in ("L","R"):
        for name in ("KIKO_GEO_cheek_fluff_"+side,"KIKO_V12_cheek_mid_"+side,"KIKO_V12_cheek_low_"+side):
            o=bpy.data.objects.get(name)
            if not o:continue
            b=o.modifiers.get("V1.2 cheek softness") or o.modifiers.new("V1.2 cheek softness","BEVEL"); b.width=.025; b.segments=3
    # Larger, tapered palms and feet with readable transitions into wrists/ankles.
    for side,s in (("L",1),("R",-1)):
        hand=bpy.data.objects["KIKO_GEO_hand_"+side]
        for v in hand.data.vertices:
            t=max(0,min(1,(.92-v.co.z)/.25))
            cx=s*.565
            v.co.x=cx+(v.co.x-cx)*(1.02+t*.14)
            v.co.y=-.055+(v.co.y+.055)*(1.0+t*.11)
            if v.co.z>.86:v.co.x=cx+(v.co.x-cx)*.86
        foot=bpy.data.objects["KIKO_GEO_foot_"+side]
        for v in foot.data.vertices:
            # Broad toe box, narrower heel, slight upper arch.
            front=max(0,min(1,(-v.co.y-.06)/.38)); cx=s*.20
            v.co.x=cx+(v.co.x-cx)*(.92+front*.22)
            if -.32<v.co.y<-.10 and v.co.z>.10:v.co.z+=.025
        for i in range(4):
            d=bpy.data.objects.get(f"KIKO_GEO_digit_{i}_{side}")
            if d:d.location.x+=s*(i-1.5)*.006
        for i in range(3):
            toe=bpy.data.objects.get(f"KIKO_GEO_toe_{i}_{side}")
            if toe:toe.location.x+=s*(i-1)*.010
    # Broaden the existing chest fan and add two short side clumps.
    for i in range(3):
        o=bpy.data.objects.get(f"KIKO_GEO_chest_tuft_{i}")
        if o:
            for v in o.data.vertices:v.co.x*=1.10
            b=o.modifiers.get("V1.2 chest softness") or o.modifiers.new("V1.2 chest softness","BEVEL"); b.width=.018; b.segments=3
    # Make the plume read at 3/4 while retaining its continuous topology.
    tail=bpy.data.objects["KIKO_GEO_tail_plume"]
    for v in tail.data.vertices:
        if v.co.y>.30:
            factor=1.10+min(.08,(v.co.y-.30)*.08)
            v.co.x*=factor
            v.co.z=.84+(v.co.z-.84)*1.075
    # Preserve current proportions; round only the perimeter and thickness.
    for side in ("L","R"):
        for prefix in ("KIKO_GEO_ear_","KIKO_GEO_ear_inner_"):
            o=bpy.data.objects[prefix+side]
            b=o.modifiers.get("V1.2 soft ear edge") or o.modifiers.new("V1.2 soft ear edge","BEVEL")
            b.width=.075 if "inner" not in prefix else .035; b.segments=5

def palette():
    colors={"fur_gray":(.20,.285,.325,1),"fur_cream":(.76,.70,.60,1),"fur_orange":(.58,.22,.075,1),"inner_ear":(.66,.28,.27,1),"iris":(.78,.34,.055,1),"scarf":(.72,.19,.04,1),"cloth":(.19,.245,.12,1),"leather":(.16,.06,.025,1),"backpack":(.22,.13,.065,1)}
    for name,c in colors.items():
        m=bpy.data.materials.get(name)
        if not m:continue
        m.diffuse_color=c; bs=m.node_tree.nodes.get("Principled BSDF") if m.use_nodes else None
        if bs:bs.inputs["Base Color"].default_value=c; bs.inputs["Roughness"].default_value=.78 if "fur" not in name else .88

def studio():
    for o in list(bpy.data.objects):
        if o.name.startswith(("STUDIO_","Key","Fill","Rim")):bpy.data.objects.remove(o,do_unlink=True)
    bgmat=bpy.data.materials.get("V12_studio") or bpy.data.materials.new("V12_studio"); bgmat.diffuse_color=(.105,.12,.135,1)
    bpy.ops.mesh.primitive_plane_add(size=18,location=(0,0,-.06)); floor=bpy.context.object; floor.name="V12_STUDIO_floor"; floor.data.materials.append(bgmat)
    world=bpy.context.scene.world; world.color=(.035,.04,.05)
    specs=[("V12_key",(-3.5,-4.5,5.5),850,5,(1,.82,.68)),("V12_fill",(4,-3,3.8),600,5,(.60,.72,1)),("V12_rim",(2.5,3.5,4),500,4,(1,.55,.32))]
    for name,loc,energy,size,color in specs:
        d=bpy.data.lights.new(name,"AREA"); d.energy=energy; d.size=size; d.shape="DISK"; d.color=color
        o=bpy.data.objects.new(name,d); bpy.context.collection.objects.link(o); o.location=loc; o.rotation_euler=(Vector((0,0,1.45))-o.location).to_track_quat("-Z","Y").to_euler()

def render_views(cam,arm):
    REVIEW.mkdir(parents=True,exist_ok=True); sc=bpy.context.scene; sc.render.engine="BLENDER_EEVEE"; sc.render.resolution_x=700; sc.render.resolution_y=700; sc.render.resolution_percentage=100; sc.render.image_settings.file_format="PNG"; sc.view_settings.look="AgX - Medium High Contrast"
    # Clear animation influence for neutral beauty evaluation.
    sc.frame_set(1)
    views=[("front",(0,-6.2,1.63),(0,0,1.48),62),("three_quarter",(4.0,-5.0,1.78),(0,0,1.50),62),("face_closeup",(0,-4.1,2.30),(0,0,2.22),74)]
    for name,loc,target,lens in views:
        cam.location=loc; cam.rotation_euler=(Vector(target)-cam.location).to_track_quat("-Z","Y").to_euler(); cam.data.lens=lens; sc.render.filepath=str(REVIEW/(name+".png")); bpy.ops.render.render(write_still=True)

def main():
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/"KIKO_master_v1_1.blend")); arm=bpy.data.objects["KIKO_RIG_armature"]
    shape_head(); shape_ears_eyes(); shape_body_limbs(); soften_crest(); modeled_fur_accents(); face_accents(); final_beauty_refinement(); palette(); studio(); arm["kiko_asset_version"]="production-v1.2-final-beauty"; arm["rig_rebuilt"]=False
    cam=bpy.data.objects["KIKO_CAM"]; bpy.ops.wm.save_as_mainfile(filepath=str(MASTER)); render_views(cam,arm); bpy.ops.wm.save_as_mainfile(filepath=str(MASTER))
    report={"source":"KIKO_master_v1_1.blend","output":MASTER.name,"armature":arm.name,"rig_rebuilt":False,"vertices":sum(len(o.data.vertices) for o in bpy.data.objects if o.type=="MESH"),"polygons":sum(len(o.data.polygons) for o in bpy.data.objects if o.type=="MESH")}
    (REVIEW/"build_report.json").write_text(json.dumps(report,indent=2))
if __name__=="__main__":main()
