"""Correct the supplied visual mesh in an isolated Stage 5 candidate.

blender --background --factory-startup --python scripts/kiko_stage5_targeted_correction.py -- \
    --name next_review --revision 3 --resolution 768

No character primitives are generated. Existing vertices are deformed; misplaced
experimental pieces are excluded. This does not grant visual approval, add fur,
retopologize, transfer a rig, or modify any source/master. Each run needs a new
output name. Review cameras fit actual object bounds, including the entire face.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "assets/characters/kiko_final/source/KIKO_source_v3_1.glb"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def smooth(a, b, value):
    t = min(1.0, max(0.0, (value - a) / (b - a)))
    return t * t * (3 - 2 * t)


def bounds(objects):
    points = [o.matrix_world @ Vector(c) for o in objects for c in o.bound_box]
    return (Vector([min(p[i] for p in points) for i in range(3)]),
            Vector([max(p[i] for p in points) for i in range(3)]))


def edit(obj, function):
    inverse = obj.matrix_world.inverted()
    for vertex in obj.data.vertices:
        vertex.co = inverse @ function(obj.matrix_world @ vertex.co)
    obj.data.update()


def center(obj):
    low, high = bounds([obj])
    return (low + high) * .5


def deform_ear(p):
    x, y, z = p
    s = 1 if x >= 0 else -1
    t = smooth(.60, 1.65, abs(x))
    x = s * (.60 + (abs(x) - .60) * .80)
    z = 2.70 + (z - 2.70) * (1 - .18 * t) - .12 * t
    y += .04 * t
    return Vector((x, y, z))


def arm(p, weight=1):
    x, y, z = p
    sign = 1 if x >= 0 else -1
    angle = math.radians(88) * weight
    dx, dz = abs(x) - .44, z - 1.57
    return Vector((sign * (.44 + math.cos(angle)*dx + math.sin(angle)*dz),
                   y, 1.57 - math.sin(angle)*dx + math.cos(angle)*dz))


def correct(objects, revision):
    removed = []
    # These experimental pieces were placed at crest height, not cheek height.
    for obj in list(objects):
        if "cheek mass " in obj.name or "tail plume form " in obj.name:
            removed.append(obj.name)
            objects.remove(obj)
            bpy.data.objects.remove(obj, do_unlink=True)
    lookup = {o.name.removeprefix("KIKO | "): o for o in objects}
    if revision == 3:
        return removed + integrated_face(objects, lookup)

    def body(p):
        x, y, z = p
        if z > 2.38 and abs(x) > .64:
            return p.lerp(deform_ear(p), smooth(.64, .84, abs(x))*smooth(2.38,2.52,z))
        if revision == 1 and .95 < z < 2.30 and abs(x) > .48:
            # Limit the rest-pose edit to exposed arms, below the ear/head zone.
            strength = smooth(.48, .76, abs(x)) * (1-smooth(2.14, 2.30, z))
            if abs(x) > .74:
                return arm(p, strength)
        if 1.76 < z < 2.82 and abs(x) < .76:
            # Broad lower cheeks; recessed sockets in the existing head surface.
            cheek = math.exp(-((z-2.01)/.24)**2)
            x *= 1 + .08 * cheek * (1-smooth(.50,.76,abs(x)))
            if y < -.16:
                r = math.sqrt(((abs(x)-.29)/.255)**2 + ((z-2.36)/.265)**2)
                socket = .045*math.exp(-(r/.75)**4) - .055*math.exp(-((r-1)/.24)**2)
                y += socket * smooth(.16, .37, -y)
        return Vector((x, y, z))

    edit(lookup["continuous sculpted body, head and ears"], body)
    for obj in objects:
        if "inner ear " in obj.name:
            edit(obj, deform_ear)
        if revision == 1 and any(t in obj.name for t in ["adventurer palm", "relaxed finger", "expressive thumb", "palm fur tuft", "forearm wrap"]):
            edit(obj, arm)

    # Reprofile the existing facial shell, rather than attach cheek spheres.
    def muzzle(p):
        x, y, z = p
        if revision >= 2:
            old_q = max(.03,1-(x/.70)**2-((z-2.18)/.72)**2)
            v = min(1,max(0,(z-1.62)/.66))
            width = max(.035+.435*math.sin(math.pi*v)**.78,.10)
            u = x/width
            old_y = .015-.52*math.sqrt(old_q)-.012-.12*math.exp(-((z-1.94)/.22)**2)*(1-.34*abs(u))
            old_y -= .045*math.exp(-((abs(u)-.72)/.21)**2-((z-1.96)/.22)**2)
            residual = min(.014,max(-.014,y-old_y))
            x *= 1.48
            z = 2.02+(z-1.95)*.76
            return Vector((x,face_surface(x,z)+residual,z))
        x *= 1.43
        z = 2.025 + (z - 1.95) * .72
        y += .025 + .018 * (abs(x)/.66)**2
        return Vector((x, y, z))

    def face_surface(x,z):
        q = max(.025,1-(x/.73)**2-((z-2.18)/.72)**2)
        return .015-.52*math.sqrt(q)-.023-.055*math.exp(-((z-2.075)/.12)**2-(x/.24)**2)

    edit(lookup["integrated cream cheeks and muzzle"], muzzle)
    for obj in objects:
        if "cheek tuft " in obj.name:
            c = center(obj)
            sign = 1 if c.x > 0 else -1
            def tuft(p, c=c, sign=sign):
                q = p-c
                return Vector((sign*(abs(c.x)+.045) + q.x*1.15,
                               -.19 + q.y*1.65,
                               2.035+(c.z-2.05)*.90+q.z*.80))
            edit(obj, tuft)
        if any(t in obj.name for t in ["soft nose", "mouth smile line", "lower lip", "cheek freckle"]):
            if revision == 1:
                edit(obj, muzzle)
            else:
                c = center(obj)
                new_z = 2.02+(c.z-1.95)*.76
                new_x = c.x*1.30
                depth = .015 if 'soft nose' in obj.name else .008
                new_c = Vector((new_x,face_surface(new_x,new_z)-depth,new_z))
                edit(obj,lambda p,c=c,new_c=new_c: new_c+Vector(((p-c).x,(p-c).y,(p-c).z*.85)))

    for obj in objects:
        if any(t in obj.name for t in ["eye sclera", "amber iris", "honey iris", "pupil ", "eye glint", "eyelid "]):
            sign = 1 if center(obj).x > 0 else -1
            def eye(p, sign=sign):
                x, y, z = p
                return Vector((sign*.305 + (x-sign*.285)*1.09,
                               y+.035, 2.345+(z-2.33)*.87))
            edit(obj, eye)
            if revision >= 2 and any(t in obj.name for t in ['amber iris','honey iris','pupil ']):
                c = center(obj)
                edit(obj,lambda p,c=c: c+Vector(((p-c).x*1.30,(p-c).y,(p-c).z*1.12)))
            if revision >= 2 and 'eye glint' in obj.name:
                c = center(obj)
                edit(obj,lambda p,c=c: c+(p-c)*.70)
        if "expressive brow " in obj.name:
            edit(obj, lambda p: Vector((p.x*1.04, p.y+.01, 2.345+(p.z-2.33)*.87)))

    for obj in objects:
        if "layered crest lock " in obj.name:
            c = center(obj)
            lo, hi = bounds([obj])
            index = int(obj.name[-2:])
            def crest(p, c=c, lo=lo, hi=hi, index=index):
                t = max(0, min(1, (p.z-lo.z)/(hi.z-lo.z)))
                return Vector((c.x+(p.x-c.x)*.83 + .085*math.sin(t*math.pi)*math.cos(index),
                               c.y+(p.y-c.y)*1.30 + .16*t*t,
                               p.z - .08*t*t))
            edit(obj, crest)

    if revision >= 2:
        for name,color in [('Eye | amber iris',(.32,.135,.025,1)),
                           ('Eye | honey iris center',(.52,.275,.065,1)),
                           ('Eye | warm ivory',(.85,.77,.63,1))]:
            material=bpy.data.materials.get(name)
            if material and material.use_nodes:
                node=next(n for n in material.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
                node.inputs['Base Color'].default_value=color
        # Narrow the tail root and move existing locks to the outer silhouette.
        # The source tail centerline is retained, with smoothly varied thickness.
        controls=[(-.08,.17,.86),(-.43,.36,.72),(-.86,.48,.70),(-1.22,.48,.83),
                  (-1.47,.43,1.08),(-1.55,.34,1.36),(-1.49,.24,1.58),(-1.35,.12,1.72)]
        path=[]
        for i in range(len(controls)-1):
            p0=Vector(controls[max(0,i-1)]);p1=Vector(controls[i])
            p2=Vector(controls[i+1]);p3=Vector(controls[min(len(controls)-1,i+2)])
            for j in range(16):
                t=j/16
                path.append(.5*((2*p1)+(-p0+p2)*t+(2*p0-5*p1+4*p2-p3)*t*t+(-p0+3*p1-3*p2+p3)*t*t*t))
        path.append(Vector(controls[-1]))
        def tail_shape(p):
            idx=min(range(len(path)),key=lambda i:(p-path[i]).length_squared)
            t=idx/(len(path)-1)
            factor=.48+.52*smooth(.05,.65,t)
            radial=p-path[idx]
            # A shallow, directional scallop in the existing surface, not noise.
            scallop=1+.065*math.sin(t*math.pi*18)*smooth(.15,.45,t)
            return path[idx]+radial*factor*scallop
        edit(lookup['dominant curved plume tail'],tail_shape)
        for obj in objects:
            if 'tail plume lock ' not in obj.name:
                continue
            index=int(obj.name[-2:])-1
            t=.26+index*.052
            idx=round(t*(len(path)-1))
            tangent=(path[min(idx+1,len(path)-1)]-path[max(0,idx-1)]).normalized()
            outward=Vector((-tangent.z,0,tangent.x)).normalized()
            if index%2:
                outward=-outward
            c=center(obj)
            width=.16+.20*math.sin(t*math.pi)
            target=path[idx]+outward*width
            def plume(p,c=c,target=target,tangent=tangent,outward=outward):
                q=p-c
                return target+outward*q.z*2.1+tangent*q.x*2.8+Vector((0,q.y*1.5,0))
            edit(obj,plume)

    return removed


def integrated_face(objects, lookup):
    """Sculpt and color the existing continuous skin instead of floating a mask.

    Starts from the source again; does not inherit the rejected arm/tail edits.
    Color defines the cream identity region; no groom or texture obscures form.
    """
    skin = lookup['continuous sculpted body, head and ears']
    def sculpt(p):
        x,y,z=p
        front=smooth(.04,.34,-y)
        lower=math.exp(-((z-2.01)/.235)**4)
        # Continuous support across the whole head, with no hard selection edge.
        side=math.exp(-((abs(x)-.49)/.23)**4)
        x += (.068 if x>=0 else -.068)*side*lower*front
        muzzle=math.exp(-((x/.49)**4)-((z-2.035)/.205)**4)
        y -= .082*muzzle*front
        socket=math.exp(-((abs(x)-.285)/.235)**4-((z-2.35)/.235)**4)
        y += .016*socket*front
        return Vector((x,y,z))
    edit(skin,sculpt)
    # The old shell is excluded after its volume has been integrated into skin.
    removed=[]
    for name in ['integrated cream cheeks and muzzle','expressive brow L','expressive brow R']:
        obj=lookup[name]
        removed.append(obj.name)
        objects.remove(obj)
        bpy.data.objects.remove(obj,do_unlink=True)

    vertices=[skin.matrix_world@v.co for v in skin.data.vertices]
    tree=BVHTree.FromPolygons(vertices,[tuple(p.vertices) for p in skin.data.polygons])
    def surface(x,z):
        hit,normal,index,distance=tree.ray_cast(Vector((x,-2,z)),Vector((0,1,0)),4)
        if hit is None:
            raise RuntimeError(f'No head surface under facial feature at {x},{z}')
        return hit.y

    for obj in list(objects):
        name=obj.name
        if any(t in name for t in ['soft nose','mouth smile line','lower lip','cheek freckle']):
            c=center(obj)
            target_z=c.z+.042
            target_x=c.x*1.12
            depth=.020 if 'soft nose' in name else .010
            target_y=surface(target_x,target_z)-depth
            edit(obj,lambda p,c=c,target_x=target_x,target_y=target_y,target_z=target_z:
                 Vector((target_x+(p-c).x,target_y+(p-c).y,target_z+(p-c).z)))
        if 'cheek tuft ' in name:
            c=center(obj)
            sign=1 if c.x>0 else -1
            index=int(name[-1])-1
            target=Vector((sign*(.61+index*.020),-.21,1.95+index*.077))
            edit(obj,lambda p,c=c,target=target:
                 target+Vector(((p-c).x*1.12,(p-c).y*.70,(p-c).z*.70)))
        if any(t in name for t in ['eye sclera','amber iris','honey iris','pupil ','eye glint','eyelid ']):
            sign=1 if center(obj).x>0 else -1
            edit(obj,lambda p,sign=sign:Vector((sign*.298+(p.x-sign*.285)*1.02,p.y+.035,2.345+(p.z-2.33)*.93)))
            if any(t in name for t in ['amber iris','honey iris','pupil ']):
                c=center(obj)
                edit(obj,lambda p,c=c:c+Vector(((p-c).x*1.23,(p-c).y,(p-c).z*1.08)))
            if 'eye glint' in name:
                c=center(obj)
                edit(obj,lambda p,c=c:c+(p-c)*.7)

    # Store a smooth cream face region on the continuous mesh, exported as COLOR_0.
    colors=skin.data.color_attributes.new(name='KIKO_face_color',type='FLOAT_COLOR',domain='POINT')
    teal=Vector((.085,.185,.195))
    cream=Vector((.78,.66,.48))
    for index,vertex in enumerate(skin.data.vertices):
        x,y,z=skin.matrix_world@vertex.co
        ellipse=(x/.735)**2+((z-1.99)/.265)**2
        amount=(1-smooth(.84,1.04,ellipse))*smooth(.10,.28,-y)
        brow_r=((abs(x)-.29)/.29)**2+((z-2.36)/.31)**2
        brow=(1-smooth(.88,1.13,brow_r))*smooth(.10,.33,-y)*smooth(2.42,2.62,z)*.65
        amount=max(amount,brow)
        color=teal.lerp(cream,amount)
        colors.data[index].color=(*color,1)
    skin.data.color_attributes.active_color=colors
    material=skin.data.materials[0].copy()
    material.name='Fur | continuous teal and cream face'
    material.use_nodes=True
    node=next(n for n in material.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    attr=material.node_tree.nodes.new('ShaderNodeVertexColor')
    attr.layer_name=colors.name
    material.node_tree.links.new(attr.outputs['Color'],node.inputs['Base Color'])
    skin.data.materials.clear()
    skin.data.materials.append(material)
    for polygon in skin.data.polygons:
        polygon.material_index=0
    for name,color in [('Eye | amber iris',(.28,.09,.016,1)),
                       ('Eye | honey iris center',(.46,.21,.04,1)),
                       ('Fur | deep teal blue-gray',(*teal,1)),
                       ('Fur | soft teal highlights',(.14,.27,.28,1)),
                       ('Fur | warm integrated cream',(*cream,1)),
                       ('Fur | pale muzzle',(*cream,1)),
                       ('Eye | warm ivory',(.86,.78,.64,1))]:
        mat=bpy.data.materials.get(name)
        if mat and mat.use_nodes:
            bsdf=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
            bsdf.inputs['Base Color'].default_value=color
    return removed


def setup_studio(objects, resolution):
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.resolution_x = resolution
    scene.render.resolution_y = resolution
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.render.film_transparent = False
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - Medium High Contrast'
    if hasattr(scene, 'eevee') and hasattr(scene.eevee, 'taa_render_samples'):
        scene.eevee.taa_render_samples = 48
    world = bpy.data.worlds.new('KIKO neutral review world')
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs['Color'].default_value = (.22,.22,.22,1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value = .35
    scene.world = world
    for name,loc,power,size in [
        ('Key',(-3,-4,6),650,4), ('Fill',(4,-2,3),350,5), ('Rim',(1,3,5),500,3)]:
        data = bpy.data.lights.new(name,'AREA')
        data.energy, data.shape, data.size = power, 'DISK', size
        obj = bpy.data.objects.new(name,data)
        scene.collection.objects.link(obj)
        obj.location = loc
        obj.rotation_euler = (Vector((0,0,1.7))-obj.location).to_track_quat('-Z','Y').to_euler()
    low, high = bounds(objects)
    bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,low.z-.012))
    floor = bpy.context.object
    floor.name = 'Review floor'
    material = bpy.data.materials.new('Neutral matte floor')
    material.use_nodes = True
    node = material.node_tree.nodes.get('Principled BSDF')
    node.inputs['Base Color'].default_value = (.18,.18,.18,1)
    node.inputs['Roughness'].default_value = .95
    floor.data.materials.append(material)
    data = bpy.data.cameras.new('Review camera')
    camera = bpy.data.objects.new('Review camera',data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.data.type = 'ORTHO'
    camera.data.lens = 65
    camera.data.dof.use_dof = False
    return scene, camera, floor


def fit(camera, objects, angle, elevation, reference_points=None):
    points = reference_points or [o.matrix_world @ Vector(c) for o in objects for c in o.bound_box]
    low = Vector([min(p[i] for p in points) for i in range(3)])
    high = Vector([max(p[i] for p in points) for i in range(3)])
    target = (low+high)/2
    a,e = math.radians(angle),math.radians(elevation)
    direction = Vector((math.sin(a)*math.cos(e),-math.cos(a)*math.cos(e),math.sin(e)))
    camera.location = target + direction*12
    rotation = (-direction).to_track_quat('-Z','Y')
    camera.rotation_euler = rotation.to_euler()
    projected = [rotation.inverted() @ (p-target) for p in points]
    xmin,xmax = min(p.x for p in projected), max(p.x for p in projected)
    ymin,ymax = min(p.y for p in projected), max(p.y for p in projected)
    shift = rotation @ Vector(((xmin+xmax)/2,(ymin+ymax)/2,0))
    camera.location += shift
    camera.data.ortho_scale = max(xmax-xmin,ymax-ymin)*1.14
    bpy.context.view_layer.update()
    return {'location':list(camera.location), 'rotation_euler':list(camera.rotation_euler),
            'ortho_scale':camera.data.ortho_scale, 'angle':angle, 'elevation':elevation,
            'method':'projected world-space bounds, 14 percent margin'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--name',required=True)
    parser.add_argument('--revision',type=int,choices=[0,1,2,3],default=3,
                        help='0: source baseline; 1/2: rejected experiments; 3: integrated face correction')
    parser.add_argument('--resolution',type=int,default=768)
    parser.add_argument('--views',default='front,three_quarter,side,back,face_closeup,tail_profile,outfit_detail,black_silhouette')
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    if not args.name.replace('_','').isalnum():
        raise ValueError('Output name must be letters, numbers or underscores')
    out = ROOT/'projects/characters/kiko/review'/('stage5_'+args.name)
    out.mkdir(exist_ok=False)
    protected = [SOURCE, ROOT/'KIKO_master_v1_1.blend', ROOT/'KIKO_master_v2.blend',
                 ROOT/'KIKO_run_test_5s.blend', ROOT/'KIKO_acting_test_8s.blend']
    hashes = {str(p.relative_to(ROOT)):sha(p) for p in protected}
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(SOURCE))
    objects = [o for o in bpy.context.scene.objects if o.type=='MESH']
    for obj in objects:
        obj.data = obj.data.copy()
    # Fixed review bounds from the unmodified source make revisions comparable.
    reference_groups={
        'full':objects,
        'face':[o for o in objects if any(n in o.name for n in ['eye sclera','eyelid','expressive brow','soft nose','cheeks and muzzle','cheek tuft'])],
        'tail':[o for o in objects if 'tail' in o.name and 'scarf' not in o.name],
        'outfit':[o for o in objects if any(n in o.name for n in ['vest','scarf','harness','belt','pouch','compass'])]}
    reference_points={key:[o.matrix_world@Vector(c) for o in group for c in o.bound_box]
                      for key,group in reference_groups.items()}
    removed = correct(objects,args.revision) if args.revision else []
    bpy.context.view_layer.update()
    blend = out/'KIKO_candidate.blend'
    glb = out/'KIKO_candidate.glb'
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.export_scene.gltf(filepath=str(glb),export_format='GLB',use_selection=True,
                              export_apply=True,export_materials='EXPORT')
    scene,camera,floor = setup_studio(objects,args.resolution)
    face = [o for o in objects if any(n in o.name for n in [
        'eye sclera','eyelid','expressive brow','soft nose','cheeks and muzzle','cheek tuft'])]
    tail = [o for o in objects if 'tail' in o.name and 'scarf' not in o.name]
    outfit = [o for o in objects if any(n in o.name for n in [
        'vest','scarf','harness','belt','pouch','compass'])]
    definitions = {
        'front':(objects,0,0), 'three_quarter':(objects,35,5),
        'side':(objects,90,0), 'back':(objects,180,0),
        'face_closeup':(face,8,0), 'tail_profile':(tail,120,5),
        'outfit_detail':(outfit,15,3),'black_silhouette':(objects,0,0)}
    cameras = {}
    fit(camera,objects,0,0,reference_points['full'])
    scene['KIKO_visual_gate'] = 'PENDING_MANUAL_REVIEW'
    scene['KIKO_source_sha256'] = hashes[str(SOURCE.relative_to(ROOT))]
    scene['KIKO_correction_revision'] = args.revision
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    for view in args.views.split(','):
        group,angle,elevation = definitions[view]
        key={'face_closeup':'face','tail_profile':'tail','outfit_detail':'outfit'}.get(view,'full')
        cameras[view] = fit(camera,group,angle,elevation,reference_points[key])
        saved_materials = {}
        if view == 'black_silhouette':
            black = bpy.data.materials.new('True black silhouette')
            black.use_nodes=True
            nodes=black.node_tree.nodes
            nodes.clear()
            emission=nodes.new('ShaderNodeEmission')
            emission.inputs['Color'].default_value=(0,0,0,1)
            output=nodes.new('ShaderNodeOutputMaterial')
            black.node_tree.links.new(emission.outputs[0],output.inputs['Surface'])
            for obj in objects:
                saved_materials[obj.name]=list(obj.data.materials)
                for i in range(len(obj.data.materials)):
                    obj.data.materials[i]=black
            floor.hide_render=True
            scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(1,1,1,1)
            scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=1
        scene.render.filepath=str(out/(view+'.png'))
        bpy.ops.render.render(write_still=True)
        if saved_materials:
            for obj in objects:
                for i,material in enumerate(saved_materials[obj.name]):
                    obj.data.materials[i]=material
            floor.hide_render=False
            scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.22,.22,.22,1)
            scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.35
    for name,digest in hashes.items():
        if sha(ROOT/name)!=digest:
            raise RuntimeError('Protected source changed: '+name)
    report = {'source':str(SOURCE.relative_to(ROOT)),'source_sha256':hashes[str(SOURCE.relative_to(ROOT))],
              'revision':args.revision,'visual_gate':'PENDING_MANUAL_REVIEW',
              'blender_version':bpy.app.version_string,'mesh_objects':len(objects),
              'vertices':sum(len(o.data.vertices) for o in objects),
              'removed_objects':removed, 'protected_hashes':hashes,
              'protected_assets_unchanged':True,'cameras':cameras,
              'artifacts':{p.name:{'bytes':p.stat().st_size,'sha256':sha(p)}
                           for p in out.iterdir() if p.suffix in ['.blend','.glb','.png']}}
    (out/'build_manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    print('KIKO_CANDIDATE_COMPLETE',out,flush=True)


if __name__=='__main__':
    main()
