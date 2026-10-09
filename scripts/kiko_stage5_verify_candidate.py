"""Check a review candidate's GLB roundtrip without modifying its blend.

This tests bounds, object preservation, finite coordinates and vertex colors.
It intentionally does not assign a visual-likeness or rig-readiness PASS.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import struct

import bpy
from mathutils import Vector


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory():
    result = {}
    for obj in bpy.context.scene.objects:
        if obj.type != 'MESH' or not obj.name.startswith('KIKO | '):
            continue
        points = [obj.matrix_world @ v.co for v in obj.data.vertices]
        if not all(math.isfinite(c) for p in points for c in p):
            raise RuntimeError('Non-finite vertex in '+obj.name)
        colors = obj.data.color_attributes.active_color
        result[obj.name] = {
            'vertices':len(points),
            'color_storage':None if colors is None else colors.data_type,
            'min':[min(p[i] for p in points) for i in range(3)],
            'max':[max(p[i] for p in points) for i in range(3)],
            'color_range':None if colors is None else {
                'min':[min(c.color[i] for c in colors.data) for i in range(4)],
                'max':[max(c.color[i] for c in colors.data) for i in range(4)]}}
    return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('candidate_dir',type=Path)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    directory=args.candidate_dir.resolve()
    out=directory/'technical_verification.json'
    if out.exists():
        raise RuntimeError('Refusing to overwrite '+str(out))
    blend=directory/'KIKO_candidate.blend'
    glb=directory/'KIKO_candidate.glb'
    hashes={p.name:digest(p) for p in [blend,glb]}
    manifest=json.loads((directory/'build_manifest.json').read_text())
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    before=inventory()
    for obj in list(bpy.context.scene.objects):
        if obj.type=='MESH' and obj.name.startswith('KIKO | '):
            bpy.data.objects.remove(obj,do_unlink=True)
    bpy.ops.import_scene.gltf(filepath=str(glb))
    after=inventory()
    if set(before)!=set(after):
        raise RuntimeError('Roundtrip object names differ')
    bounds_error=max(abs(before[name][key][i]-after[name][key][i])
                     for name in before for key in ['min','max'] for i in range(3))
    skin='KIKO | continuous sculpted body, head and ears'
    if before[skin]['color_range'] is None or after[skin]['color_range'] is None:
        raise RuntimeError('Continuous face color attribute missing')
    color_error=max(abs(before[skin]['color_range'][key][i]-after[skin]['color_range'][key][i])
                    for key in ['min','max'] for i in range(4))
    raw=glb.read_bytes()
    json_size=struct.unpack_from('<I',raw,12)[0]
    document=json.loads(raw[20:20+json_size])
    mesh=next(m for m in document['meshes'] if 'Continuous_Skin' in m['name'])
    accessor=document['accessors'][mesh['primitives'][0]['attributes']['COLOR_0']]
    if accessor['componentType']!=5126 or accessor['type']!='VEC3':
        raise RuntimeError('Expected float RGB export for the continuous face')
    view=document['bufferViews'][accessor['bufferView']]
    offset=28+json_size+view.get('byteOffset',0)+accessor.get('byteOffset',0)
    stride=view.get('byteStride',12)
    exported=[struct.unpack_from('<3f',raw,offset+i*stride) for i in range(accessor['count'])]
    export_range={'min':[min(c[i] for c in exported) for i in range(3)],
                  'max':[max(c[i] for c in exported) for i in range(3)]}
    export_color_error=max(abs(before[skin]['color_range'][key][i]-export_range[key][i])
                           for key in ['min','max'] for i in range(3))
    # Blender's importer stores COLOR_0 as BYTE_COLOR: permit one sRGB byte step
    # in linear space, while requiring the GLB's actual floats to remain exact.
    color_tolerance=(1-((254/255+.055)/1.055)**2.4
                     if after[skin]['color_storage']=='BYTE_COLOR' else 1e-6)
    if bounds_error>1e-5 or export_color_error>1e-6 or color_error>color_tolerance:
        raise RuntimeError(f'Roundtrip errors: bounds={bounds_error}, colors={color_error}')
    rendered={}
    for view in ['front','face_closeup']:
        camera=bpy.context.scene.camera
        settings=manifest['cameras'][view]
        camera.location=settings['location']
        camera.rotation_euler=settings['rotation_euler']
        camera.data.ortho_scale=settings['ortho_scale']
        bpy.context.view_layer.update()
        path=directory/('roundtrip_'+view+'.png')
        bpy.context.scene.render.filepath=str(path)
        bpy.ops.render.render(write_still=True)
        rendered[path.name]={'sha256':digest(path),'bytes':path.stat().st_size}
    for p in [blend,glb]:
        if digest(p)!=hashes[p.name]:
            raise RuntimeError('Candidate source unexpectedly modified')
    report={'export_preservation_gate':'PASS',
            'scope':'Object names, finite vertices, world bounds, face vertex-color extrema; visual review remains separate.',
            'source_sha256':hashes,'objects_before':len(before),'objects_after':len(after),
            'maximum_bounds_error':bounds_error,'bounds_tolerance':1e-5,
            'face_color_export_maximum_error':export_color_error,'export_color_tolerance':1e-6,
            'face_color_import_maximum_error':color_error,'import_color_tolerance':color_tolerance,
            'import_color_storage':after[skin]['color_storage'],
            'candidate_files_unchanged':True,'roundtrip_renders':rendered,
            'visual_gate':'NOT_ASSESSED_BY_THIS_SCRIPT'}
    out.write_text(json.dumps(report,indent=2)+'\n')
    print('KIKO_EXPORT_PRESERVATION_PASS',out,flush=True)


if __name__=='__main__':
    main()
