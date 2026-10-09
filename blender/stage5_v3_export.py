"""
Stage 5.1 — Export V3 GLB from saved blend and verify roundtrip.
"""
import bpy
import os
import json

PROJECT = "/Users/macbook/Automation-Workplace/cartoon-maker"
BLEND_V3 = os.path.join(PROJECT, "projects/characters/kiko/blends/master/KIKO_visual_stage5_v3.blend")
GLB_V3 = os.path.join(PROJECT, "assets/characters/kiko_final/source/KIKO_source_v3.glb")

# Open saved blend
bpy.ops.wm.open_mainfile(filepath=BLEND_V3)

# Print available export params
print("=== Checking gltf export params ===")

# Count stats
final_objects = len([o for o in bpy.data.objects if o.type == 'MESH'])
final_verts = sum(len(o.data.vertices) for o in bpy.data.objects if o.type == 'MESH')
final_faces = sum(len(o.data.polygons) for o in bpy.data.objects if o.type == 'MESH')
print(f"Mesh objects: {final_objects}")
print(f"Vertices: {final_verts}")
print(f"Faces: {final_faces}")

# Export GLB - use only standard params
os.makedirs(os.path.dirname(GLB_V3), exist_ok=True)

bpy.ops.export_scene.gltf(
    filepath=GLB_V3,
    export_format='GLB',
    use_selection=False,
    export_apply=True,
    export_materials='EXPORT',
    export_normals=True,
)
print(f"Exported: {GLB_V3}")

fsize = os.path.getsize(GLB_V3)
print(f"File size: {fsize} bytes ({fsize/1024/1024:.1f} MB)")

# === VERIFY GLB ROUNDTRIP ===
print("\n=== GLB Roundtrip Verification ===")
bpy.ops.wm.read_homefile(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB_V3)

reimport_objects = len([o for o in bpy.data.objects if o.type == 'MESH'])
reimport_verts = sum(len(o.data.vertices) for o in bpy.data.objects if o.type == 'MESH')
print(f"Re-imported: {reimport_objects} mesh objects, {reimport_verts} verts")

mat_check = {}
for mat in bpy.data.materials:
    if mat.use_nodes:
        for node in mat.node_tree.nodes:
            if node.type == 'BSDF_PRINCIPLED':
                bc = node.inputs['Base Color'].default_value
                is_white = (bc[0] > 0.95 and bc[1] > 0.95 and bc[2] > 0.95)
                mat_check[mat.name] = {
                    "base_color": [round(bc[0], 3), round(bc[1], 3), round(bc[2], 3)],
                    "is_white": is_white,
                    "roughness": round(node.inputs['Roughness'].default_value, 3),
                }

white_count = sum(1 for v in mat_check.values() if v["is_white"])
total_mats = len(mat_check)

print(f"\nMaterials: {total_mats}")
print(f"White after roundtrip: {white_count}")
for name, info in sorted(mat_check.items()):
    status = "WHITE!" if info["is_white"] else "OK"
    print(f"  {status} {name}: BC={info['base_color']} R={info['roughness']}")

# Save report
report = {
    "glb": GLB_V3,
    "file_size_bytes": fsize,
    "export_objects": final_objects,
    "export_verts": final_verts,
    "reimport_objects": reimport_objects,
    "reimport_verts": reimport_verts,
    "total_materials": total_mats,
    "white_materials": white_count,
    "materials": mat_check,
    "material_export_pass": white_count == 0
}

report_path = os.path.join(PROJECT, "projects/characters/kiko/reports/v3_glb_roundtrip.json")
os.makedirs(os.path.dirname(report_path), exist_ok=True)
with open(report_path, 'w') as f:
    json.dump(report, f, indent=2)

print(f"\nMaterial export: {'PASS' if white_count == 0 else 'FAIL'}")
print(f"Report: {report_path}")
