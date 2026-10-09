"""
Stage 5 — Inspect KIKO_source_v2.glb
Reports mesh topology, materials, vertex counts, bounding box, and structure.
"""
import bpy
import json
import os
import sys

PROJECT = "/Users/macbook/Automation-Workplace/cartoon-maker"
GLB = os.path.join(PROJECT, "assets/characters/kiko_final/source/KIKO_source_v2.glb")
OUT = os.path.join(PROJECT, "review/kiko_visual/glb_inspection.json")

os.makedirs(os.path.dirname(OUT), exist_ok=True)

# Clean scene
bpy.ops.wm.read_homefile(use_empty=True)

# Import GLB
bpy.ops.import_scene.gltf(filepath=GLB)

report = {
    "source": GLB,
    "objects": [],
    "total_vertices": 0,
    "total_faces": 0,
    "total_materials": 0,
    "bounding_box": None,
    "armatures": [],
    "empties": [],
    "material_names": [],
}

all_min = [float('inf')] * 3
all_max = [float('-inf')] * 3

for obj in bpy.data.objects:
    info = {
        "name": obj.name,
        "type": obj.type,
    }

    if obj.type == 'MESH':
        mesh = obj.data
        verts = len(mesh.vertices)
        faces = len(mesh.polygons)
        edges = len(mesh.edges)
        info["vertices"] = verts
        info["faces"] = faces
        info["edges"] = edges
        info["materials"] = [m.name if m else "None" for m in obj.data.materials]
        report["total_vertices"] += verts
        report["total_faces"] += faces

        # Shape keys
        if mesh.shape_keys:
            info["shape_keys"] = [kb.name for kb in mesh.shape_keys.key_blocks]
        else:
            info["shape_keys"] = []

        # Bounding box in world space
        for v in mesh.vertices:
            co = obj.matrix_world @ v.co
            for i in range(3):
                all_min[i] = min(all_min[i], co[i])
                all_max[i] = max(all_max[i], co[i])

        # UV maps
        info["uv_maps"] = [uv.name for uv in mesh.uv_layers]

        # Vertex groups
        info["vertex_groups"] = [vg.name for vg in obj.vertex_groups]

    elif obj.type == 'ARMATURE':
        arm = obj.data
        info["bones"] = [b.name for b in arm.bones]
        info["bone_count"] = len(arm.bones)
        report["armatures"].append(obj.name)

    elif obj.type == 'EMPTY':
        report["empties"].append(obj.name)

    report["objects"].append(info)

# Collect all material names
for mat in bpy.data.materials:
    report["material_names"].append(mat.name)
report["total_materials"] = len(report["material_names"])

if all_min[0] != float('inf'):
    report["bounding_box"] = {
        "min": [round(v, 4) for v in all_min],
        "max": [round(v, 4) for v in all_max],
        "size": [round(all_max[i] - all_min[i], 4) for i in range(3)],
    }

with open(OUT, 'w') as f:
    json.dump(report, f, indent=2)

print("=== GLB INSPECTION COMPLETE ===")
print(f"Objects: {len(report['objects'])}")
print(f"Total vertices: {report['total_vertices']}")
print(f"Total faces: {report['total_faces']}")
print(f"Total materials: {report['total_materials']}")
print(f"Armatures: {report['armatures']}")
if report['bounding_box']:
    bb = report['bounding_box']
    print(f"Bounding box size: {bb['size']}")
print(f"Report saved to: {OUT}")
