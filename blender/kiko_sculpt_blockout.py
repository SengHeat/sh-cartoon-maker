#!/usr/bin/env python3
"""Unrigged, reference-first KIKO clay sculpt blockout.

No production rig or animation data is loaded.  The purpose of this file is to
judge silhouette and proportion against assets/hero/kiko.png before retopology.
"""
from pathlib import Path
import bpy, math, json
from mathutils import Vector

BLENDER_DIR=Path(__file__).resolve().parent; ROOT=BLENDER_DIR.parent; OUT=ROOT/"review"/"kiko_sculpt_blockout"; BLEND=BLENDER_DIR/"KIKO_sculpt_blockout_v001.blend"

def material(name,color,rough=.92):
    m=bpy.data.materials.new(name); m.use_nodes=True
    p=m.node_tree.nodes.get("Principled BSDF"); p.inputs["Base Color"].default_value=(*color,1); p.inputs["Roughness"].default_value=rough
    return m

def smooth(o,sub=1):
    if o.type=="MESH":
        for p in o.data.polygons:p.use_smooth=True
        if sub:
            s=o.modifiers.new("Sculpt surface","SUBSURF");s.levels=1;s.render_levels=sub
    return o

def metabody(name, blobs, mat, resolution=.055):
    d=bpy.data.metaballs.new(name+"_field");d.resolution=resolution;d.render_resolution=resolution*.55;d.threshold=.62
    o=bpy.data.objects.new(name,d);bpy.context.collection.objects.link(o)
    for loc,scale,stiff in blobs:
        e=d.elements.new();e.type='ELLIPSOID';e.co=loc;e.radius=1;e.size_x=scale[0];e.size_y=scale[1];e.size_z=scale[2];e.stiffness=stiff
    o.data.materials.append(mat);bpy.context.view_layer.objects.active=o;o.select_set(True);bpy.ops.object.convert(target='MESH');return smooth(bpy.context.object,0)

def path_loft(name, centers, radii, mat, sides=20):
    verts=[];faces=[]
    for i,c in enumerate(centers):
        t=(Vector(centers[min(i+1,len(centers)-1)])-Vector(centers[max(0,i-1)])).normalized()
        n=t.cross(Vector((0,1,0)))
        if n.length<.1:n=t.cross(Vector((1,0,0)))
        n.normalize();b=t.cross(n).normalized();rx,ry=radii[i]
        for j in range(sides):
            a=math.tau*j/sides;verts.append(Vector(c)+n*math.cos(a)*rx+b*math.sin(a)*ry)
    faces.append(tuple(reversed(range(sides))))
    for i in range(len(centers)-1):
        for j in range(sides):
            a=i*sides+j;b=i*sides+(j+1)%sides;faces.append((a,b,b+sides,a+sides))
    faces.append(tuple(range((len(centers)-1)*sides,len(centers)*sides)))
    me=bpy.data.meshes.new(name+"_mesh");me.from_pydata(verts,[],faces);me.materials.append(mat)
    o=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(o);return smooth(o,2)

def ear_shell(side, clay, inner):
    s=side
    centers=[(s*.33,.00,2.33),(s*.56,.01,2.35),(s*.84,.03,2.36),(s*1.10,.06,2.32),(s*1.27,.09,2.25)]
    radii=[(.15,.11),(.25,.14),(.28,.14),(.19,.10),(.025,.020)]
    outer=path_loft("SCULPT_ear_L" if s>0 else "SCULPT_ear_R",centers,radii,clay,24)
    # Inset organic inner volume, not a flat decal.
    ic=[(x,-.115,z+.01) for x,y,z in centers[:-1]];ir=[(.07,.030),(.14,.040),(.15,.040),(.045,.018)]
    path_loft("SCULPT_inner_ear_L" if s>0 else "SCULPT_inner_ear_R",ic,ir,inner,18)
    return outer

def ell(name,loc,scale,mat):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3,radius=1,location=loc);o=bpy.context.object;o.name=name;o.scale=scale;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(mat);return smooth(o,1)

def build():
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    clay=material("clay_fur",(.32,.39,.39)); cream=material("clay_cream",(.62,.58,.50)); dark=material("clay_eye",(.025,.022,.019),.28)
    leather=material("clay_outfit",(.23,.17,.12)); inner=material("clay_inner_ear",(.48,.30,.27)); scarf=material("clay_scarf",(.43,.20,.13))
    # One broad organic skull with temple and jaw masses merged into a continuous surface.
    head=metabody("SCULPT_head",[
        ((0,.02,2.22),(.48,.37,.43),2.0),((0,.04,2.43),(.40,.34,.30),1.7),
        ((-.34,-.01,2.08),(.30,.29,.25),1.6),((.34,-.01,2.08),(.30,.29,.25),1.6),
        ((-.23,.01,1.94),(.34,.29,.24),1.5),((.23,.01,1.94),(.34,.29,.24),1.5),
        ((0,.02,1.78),(.30,.27,.25),1.4),
    ],clay)
    # Cream facial plane is shallow and overlapping, with tapered sides rather than balls.
    face=metabody("SCULPT_face_mask",[
        ((0,-.345,2.17),(.35,.10,.28),1.7),((-.27,-.31,2.03),(.31,.12,.19),1.55),((.27,-.31,2.03),(.31,.12,.19),1.55),
        ((-.10,-.40,2.00),(.17,.10,.13),1.4),((.10,-.40,2.00),(.17,.10,.13),1.4),
        ((0,-.33,1.91),(.29,.09,.15),1.45),
    ],cream,.04)
    # Eyes are nested into the face mask and slightly tilted, not projected toy balls.
    for s,side in ((1,"L"),(-1,"R")):
        e=ell("SCULPT_eye_"+side,(s*.185,-.402,2.225),(.122,.055,.142),cream);e.rotation_euler.y=s*math.radians(7)
        ell("SCULPT_iris_"+side,(s*.185,-.453,2.220),(.067,.013,.082),dark)
        path_loft("SCULPT_upper_lid_"+side,[(s*.30,-.467,2.25),(s*.185,-.478,2.345),(s*.07,-.465,2.27)],[(.020,.015),(.025,.018),(.018,.013)],clay,12)
        ear_shell(s,clay,inner)
    ell("SCULPT_nose",(0,-.535,2.075),(.055,.035,.040),inner)
    # Messy swept crest: overlapping hooked organic locks with varied roots and directions.
    locks=[(-.34,2.39,-.18,.25),(-.27,2.44,-.40,.35),(-.19,2.48,-.26,.45),(-.10,2.50,-.48,.53),(.00,2.51,-.23,.57),(.10,2.49,-.34,.52),(.19,2.46,-.08,.45),(.27,2.42,-.20,.36),(.34,2.38,.04,.27)]
    for i,(x,z,lean,h) in enumerate(locks):
        path_loft(f"SCULPT_crest_{i}",[(x,.03,z),(x+lean*.12,.01,z+h*.25),(x+lean*.42,-.01,z+h*.62),(x+lean*.82,-.02,z+h*.94),(x+lean,-.015,z+h)],[(.17,.14),(.17,.135),(.14,.11),(.08,.055),(.026,.020)],clay,20)
    # Compact stocky torso and neck blended from large sculpt masses.
    metabody("SCULPT_body",[((0,.02,1.48),(.52,.35,.39),1.8),((0,.02,1.27),(.55,.38,.44),1.8),((0,.01,1.04),(.49,.37,.36),1.7),((0,.02,.84),(.39,.32,.27),1.5)],clay)
    # Layered cream chest fur mass and irregular dangling locks.
    metabody("SCULPT_chest",[((0,-.315,1.38),(.25,.09,.27),1.6),((0,-.33,1.15),(.30,.10,.27),1.5),((0,-.31,.98),(.22,.09,.18),1.4)],cream,.045)
    for i,(x,z) in enumerate(((-.22,1.19),(.20,1.17),(-.14,1.00),(.12,.98),(0,.86))):
        path_loft(f"SCULPT_chest_lock_{i}",[(x,-.34,z),(x*1.12,-.35,z-.16)],[(.09,.045),(.018,.010)],cream,14)
    # Tapered limbs use blended muscle/paw masses, never cylinders.
    for s,side in ((1,"L"),(-1,"R")):
        metabody("SCULPT_arm_"+side,[((s*.41,0,1.42),(.21,.19,.25),1.5),((s*.48,-.015,1.21),(.19,.18,.24),1.5),((s*.51,-.04,1.02),(.17,.16,.19),1.4)],clay,.045)
        blobs=[((s*.51,-.07,.88),(.21,.19,.19),1.6)]
        for j in range(4):blobs.append(((s*(.39+j*.078),-.19,.80-j*.004),(.067,.110,.064),1.25))
        metabody("SCULPT_hand_"+side,blobs,clay,.035)
        metabody("SCULPT_leg_"+side,[((s*.22,.01,.72),(.24,.22,.27),1.6),((s*.22,.02,.51),(.22,.21,.23),1.5),((s*.23,.00,.33),(.19,.19,.19),1.4)],clay,.045)
        fblobs=[((s*.23,-.15,.16),(.26,.34,.16),1.6)]
        for j in range(4):fblobs.append(((s*(.085+j*.090),-.42,.11),(.075,.125,.068),1.25))
        metabody("SCULPT_foot_"+side,fblobs,clay,.035)
    # Full plume plus irregular perimeter locks. Its S-curve follows the reference turnaround.
    tc=[(0,.18,.82),(0,.38,.65),(0,.65,.58),(0,.91,.67),(0,1.14,.84),(0,1.33,1.04),(0,1.43,1.22)]
    tail=path_loft("SCULPT_tail",tc,[(.18,.17),(.25,.23),(.31,.28),(.32,.29),(.28,.25),(.21,.18),(.06,.05)],clay,26)
    for i,(y,z,sgn) in enumerate(((.42,.62,-1),(.54,.55,1),(.70,.55,-1),(.86,.63,1),(1.03,.74,-1),(1.17,.88,1),(1.30,1.03,-1))):
        path_loft(f"SCULPT_tail_lock_{i}",[(0,y,z),(sgn*.18,y+.05,z+.03),(sgn*.34,y+.08,z+.08)],[(.16,.12),(.12,.085),(.022,.015)],clay,16)
    # Silhouette-only layered explorer kit for the likeness gate.
    metabody("SCULPT_tunic",[((0,-.04,1.36),(.46,.35,.37),1.6),((0,-.03,1.11),(.43,.34,.31),1.5)],leather,.05)
    path_loft("SCULPT_scarf",[(-.28,-.02,1.69),(0,-.29,1.64),(.28,-.02,1.69),(0,.22,1.70),(-.28,-.02,1.69)],[(.085,.075)]*5,scarf,18)
    ell("SCULPT_pack",(0,.33,1.24),(.32,.20,.38),leather)
    ell("SCULPT_pouch_L",(.37,-.17,.96),(.16,.11,.18),leather);ell("SCULPT_pouch_R",(-.34,-.16,1.00),(.13,.10,.15),leather)
    for s,side in ((1,"L"),(-1,"R")):
        path_loft("SCULPT_strap_"+side,[(s*.25,-.31,1.52),(s*.09,-.36,1.01)],[(.033,.025),(.033,.025)],leather,10)
        path_loft("SCULPT_ankle_wrap_"+side,[(s*.23,-.02,.30),(s*.23,-.05,.21)],[(.18,.03),(.17,.03)],scarf,16)
    return head

def studio():
    floor=material("studio",(.075,.075,.072));bpy.ops.mesh.primitive_plane_add(size=20,location=(0,0,-.01));bpy.context.object.data.materials.append(floor)
    bpy.context.scene.world.color=(.028,.028,.026)
    for name,loc,energy,size,color in [("key",(-4,-5,6),1000,5.5,(1,.88,.75)),("fill",(4,-4,4),700,5,(.65,.75,1)),("rim",(2,4,5),650,4,(1,.68,.45))]:
        d=bpy.data.lights.new(name,'AREA');d.energy=energy;d.shape='DISK';d.size=size;d.color=color;o=bpy.data.objects.new(name,d);bpy.context.collection.objects.link(o);o.location=loc;o.rotation_euler=(Vector((0,0,1.35))-o.location).to_track_quat('-Z','Y').to_euler()
    d=bpy.data.cameras.new("SCULPT_CAM_data");c=bpy.data.objects.new("SCULPT_CAM",d);bpy.context.collection.objects.link(c);bpy.context.scene.camera=c;return c

def render(cam):
    OUT.mkdir(parents=True,exist_ok=True);s=bpy.context.scene;s.render.engine='BLENDER_EEVEE';s.render.resolution_x=700;s.render.resolution_y=700;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG';s.view_settings.look='AgX - Medium High Contrast'
    views=[('front',(0,-6.5,1.55),(0,0,1.45),65),('three_quarter',(4.2,-5.4,1.70),(0,0,1.48),66),('side',(6.5,0,1.60),(0,0,1.45),68),('back',(0,6.5,1.60),(0,0,1.45),65),('face_closeup',(0,-4.2,2.25),(0,0,2.20),78)]
    for n,loc,target,lens in views:
        cam.location=loc;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.lens=lens;s.render.filepath=str(OUT/(n+'.png'));bpy.ops.render.render(write_still=True)

def main():
    build();cam=studio();bpy.ops.wm.save_as_mainfile(filepath=str(BLEND));render(cam);bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
    meshes=[o for o in bpy.data.objects if o.type=='MESH']
    report={'stage':'unrigged_clay_likeness_gate','reference':'assets/hero/kiko.png','armature_present':False,'vertices':sum(len(o.data.vertices) for o in meshes),'polygons':sum(len(o.data.polygons) for o in meshes)}
    (OUT/'build_report.json').write_text(json.dumps(report,indent=2))
if __name__=='__main__':main()
