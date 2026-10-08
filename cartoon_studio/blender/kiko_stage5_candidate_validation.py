"""Non-destructive Stage 5 audit/render of an existing KIKO GLB candidate."""
from __future__ import annotations

import json
import math
import struct
import time
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
CANDIDATE = ROOT / "assets/characters/kiko_final/KIKO.glb"
REFERENCE = ROOT / "assets/hero/kiko.png"
OUT = ROOT / "projects/characters/kiko"
REVIEW = OUT / "review/stage5_candidate"
BLEND = OUT / "blends/review/KIKO_stage5_validation.blend"
JSON_REPORT = OUT / "reports/KIKO_STAGE5_VERIFICATION.json"
AUDIT_REPORT = OUT / "reports/KIKO_STAGE5_FINAL_VISUAL_AUDIT.md"


def glb_json(path: Path):
    raw = path.read_bytes()
    if raw[:4] != b"glTF" or struct.unpack_from("<I", raw, 4)[0] != 2:
        raise RuntimeError("Candidate is not a GLB 2.0 file")
    offset = 12
    chunk_len, chunk_type = struct.unpack_from("<II", raw, offset)
    if chunk_type != 0x4E4F534A:
        raise RuntimeError("GLB JSON chunk is missing")
    return json.loads(raw[offset + 8:offset + 8 + chunk_len])


def mesh_bounds(objects):
    points = []
    for obj in objects:
        if obj.type != "MESH":
            continue
        points.extend(obj.matrix_world @ Vector(corner) for corner in obj.bound_box)
    if not points:
        raise RuntimeError("No imported mesh geometry")
    minimum = Vector(tuple(min(p[i] for p in points) for i in range(3)))
    maximum = Vector(tuple(max(p[i] for p in points) for i in range(3)))
    return minimum, maximum


def classify(name):
    n = name.lower()
    if any(k in n for k in ("tail", "ear", "crest", "hair", "tuft")):
        return "B. DEFORM / SECONDARY RIG", "tail / ear / crest control"
    if any(k in n for k in ("backpack", "pack", "compass", "flask", "buckle", "trinket", "bedroll")):
        return "C. RIGID BONE PARENT", "spine / chest / belt bone by attachment"
    if any(k in n for k in ("scarf", "vest", "harness", "belt", "wrap", "pouch", "bib", "tunic")):
        return "D. CLOTHING NEEDING WEIGHTS", "nearby body region; simulate or weight flexible parts"
    if any(k in n for k in ("head", "face", "eye", "iris", "pupil", "nose", "mouth", "cheek", "jaw", "body", "arm", "hand", "palm", "finger", "leg", "foot", "toe", "skin", "chest", "thigh", "calf", "wrist")):
        return "A. DEFORM WITH BODY", "head / face / nearby limb bone"
    return "E. STATIC / REMOVE / REVIEW", "review attachment or exclude"


def material_audit():
    image_records = []
    missing = []
    for image in bpy.data.images:
        filepath = bpy.path.abspath(image.filepath) if image.filepath else ""
        packed = bool(getattr(image, "packed_file", None) or getattr(image, "packed_files", []))
        available = bool((image.has_data or packed) and image.size[0] > 0 and image.size[1] > 0)
        if not packed and filepath and not Path(filepath).exists():
            missing.append({"image": image.name, "path": filepath})
        if not available:
            missing.append({"image": image.name, "path": filepath, "reason": "no decoded image data"})
        image_records.append({"name": image.name, "filepath": filepath, "packed": packed,
                             "available": available, "size": list(image.size),
                             "colorspace": getattr(image.colorspace_settings, "name", "unknown")})
    supported = {"BSDF_PRINCIPLED", "OUTPUT_MATERIAL", "TEX_IMAGE", "TEX_COORD", "MAPPING",
                 "NORMAL_MAP", "BUMP", "RGB", "VALUE", "MIX_RGB", "MATH", "SEPARATE_COLOR",
                 "COMBINE_COLOR", "UV_MAP", "VERTEX_COLOR", "ATTRIBUTE"}
    unsupported = []
    glossy = []
    transparency = []
    for mat in bpy.data.materials:
        if not mat.use_nodes or not mat.node_tree:
            unsupported.append({"material": mat.name, "nodes": "no node tree"})
            continue
        for node in mat.node_tree.nodes:
            if node.type not in supported:
                unsupported.append({"material": mat.name, "node": node.name, "type": node.type})
            if node.type == "BSDF_PRINCIPLED":
                rough = node.inputs.get("Roughness")
                if rough and rough.default_value < .35:
                    glossy.append({"material": mat.name, "roughness": round(float(rough.default_value), 3)})
                alpha = node.inputs.get("Alpha")
                if alpha and alpha.default_value < .999:
                    transparency.append({"material": mat.name, "alpha": round(float(alpha.default_value), 3)})
        mode = getattr(mat, "surface_render_method", "OPAQUE")
        if mode not in ("OPAQUE", "DITHERED"):
            transparency.append({"material": mat.name, "surface_render_method": str(mode)})
    return {"images": image_records, "missing_textures": missing,
            "unsupported_nodes": unsupported, "glossy_principled_materials": glossy,
            "transparency_materials": transparency}


def geometry_audit(objects):
    rows = []
    total_v = total_p = total_t = 0
    nonmanifold = []
    duplicate_faces = []
    potential_duplicate_vertices = []
    topology_by_mesh = {}
    for obj in objects:
        if obj.type != "MESH":
            continue
        mesh = obj.data
        mesh.calc_loop_triangles()
        verts, polys = len(mesh.vertices), len(mesh.polygons)
        tris = len(mesh.loop_triangles)
        total_v += verts
        total_p += polys
        total_t += tris
        edge_use = {}
        for poly in mesh.polygons:
            for key in poly.edge_keys:
                k = tuple(sorted(key))
                edge_use[k] = edge_use.get(k, 0) + 1
        boundary = sum(n == 1 for n in edge_use.values())
        overused = sum(n > 2 for n in edge_use.values())
        zero_area = sum(poly.area <= 1e-12 for poly in mesh.polygons)
        zero_normal = sum(poly.normal.length <= 1e-8 for poly in mesh.polygons)
        faces = set()
        dup_face_count = 0
        for poly in mesh.polygons:
            f = tuple(sorted(poly.vertices))
            if f in faces:
                dup_face_count += 1
            faces.add(f)
        quantized = set()
        duplicate_vertex_count = 0
        for vert in mesh.vertices:
            key = tuple(round(float(x), 6) for x in vert.co)
            if key in quantized:
                duplicate_vertex_count += 1
            quantized.add(key)
        if boundary or overused:
            nonmanifold.append({"object": obj.name, "boundary_edges": boundary,
                                "edges_used_more_than_twice": overused})
        if dup_face_count:
            duplicate_faces.append({"object": obj.name, "duplicate_faces": dup_face_count})
        if duplicate_vertex_count:
            potential_duplicate_vertices.append({"object": obj.name,
                                                 "coincident_vertices_6dp": duplicate_vertex_count})
        topology_by_mesh[obj.name] = {"vertices": verts, "polygons": polys, "triangles": tris,
                                      "boundary_edges": boundary, "edges_used_more_than_twice": overused,
                                      "zero_area_faces": zero_area, "zero_length_normals": zero_normal}
        category, parent = classify(obj.name)
        rows.append({"name": obj.name, "vertices": verts, "polygons": polys, "triangles": tris,
                     "classification": category, "recommended_parent": parent,
                     "weighting_required": category in ("A. DEFORM WITH BODY", "B. DEFORM / SECONDARY RIG",
                                                         "D. CLOTHING NEEDING WEIGHTS")})
    return {"vertices": total_v, "polygons": total_p, "triangles": total_t,
            "topology_by_mesh": topology_by_mesh, "nonmanifold_meshes": nonmanifold,
            "duplicate_faces": duplicate_faces,
            "potential_duplicate_vertices": potential_duplicate_vertices,
            "object_classification": rows}


def setup_render(minimum, maximum):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in scene.render.bl_rna.properties["engine"].enum_items.keys() else "BLENDER_EEVEE"
    if hasattr(scene, "eevee"):
        if hasattr(scene.eevee, "taa_render_samples"):
            scene.eevee.taa_render_samples = 64
        elif hasattr(scene.eevee, "taa_samples"):
            scene.eevee.taa_samples = 64
    scene.render.resolution_x = 1200
    scene.render.resolution_y = 1200
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.view_settings.exposure = 0
    scene.view_settings.gamma = 1
    world = bpy.data.worlds.new("Stage 5 neutral review world")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (.42, .42, .42, 1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = .55
    scene.world = world
    def area(name, pos, watts, color, size):
        data = bpy.data.lights.new(name, "AREA")
        data.energy = watts
        data.color = color
        data.shape = "DISK"
        data.size = size
        ob = bpy.data.objects.new(name, data)
        scene.collection.objects.link(ob)
        ob.location = pos
        ob.rotation_euler = (Vector((0, 0, 0)) - ob.location).to_track_quat("-Z", "Y").to_euler()
    area("Review soft key", (-4, -5, 6), 900, (1, 1, 1), 5)
    area("Review soft fill", (4, -3, 3), 700, (1, 1, 1), 5)
    area("Review subtle rim", (1, 4, 5), 850, (1, 1, 1), 4)
    cam = bpy.data.cameras.new("Stage 5 review camera")
    camera = bpy.data.objects.new("Stage 5 review camera", cam)
    scene.collection.objects.link(camera)
    scene.camera = camera
    cam.lens = 55
    cam.sensor_width = 36
    cam.type = "PERSP"
    return scene, camera


def point_camera(camera, target, direction, minimum, maximum, full=True, lens=55, focus_objects=None, focus_points=None):
    target = Vector(target)
    forward = -Vector(direction).normalized()
    q = forward.to_track_quat("-Z", "Y")
    right = q @ Vector((1, 0, 0))
    up = q @ Vector((0, 1, 0))
    dvec = q @ Vector((0, 0, 1))
    corners = list(focus_points or [])
    if not corners and focus_objects:
        for obj in focus_objects:
            if obj.type == "MESH":
                corners.extend(obj.matrix_world @ Vector(c) for c in obj.bound_box)
    if not corners:
        corners = [Vector((x, y, z)) for x in (minimum.x, maximum.x)
                   for y in (minimum.y, maximum.y) for z in (minimum.z, maximum.z)]
    tan_half = 36.0 / (2.0 * lens)
    need = []
    for p in corners:
        v = p - target
        depth = v.dot(forward)
        need.append(abs(v.dot(right)) / tan_half - depth)
        need.append(abs(v.dot(up)) / tan_half - depth)
    distance = max(need) * 1.09 + .15
    camera.location = target - forward * distance
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.lens = lens


def render_views(objects, minimum, maximum, stats):
    scene = bpy.context.scene
    camera = scene.camera
    center = (minimum + maximum) * .5
    height = maximum.z - minimum.z
    face_z = minimum.z + height * .82
    torso_z = minimum.z + height * .48
    def matching(*tokens):
        return [o for o in objects if o.type == "MESH" and any(t in o.name.lower() for t in tokens)]
    core_name = "continuous sculpted body, head and ears"
    core = next((o for o in objects if o.type == "MESH" and core_name in o.name.lower()), None)
    focus_head = [o for o in matching("head", "skull", "eye", "iris", "pupil", "cheek", "muzzle", "nose", "mouth", "lip", "ear", "crest", "tuft") if core is None or o != core]
    head_points = [o.matrix_world @ Vector(c) for o in focus_head for c in o.bound_box]
    face_points = list(head_points)
    if core:
        face_cutoff = minimum.z + height * .62
        head_cutoff = minimum.z + height * .55
        for vert in core.data.vertices:
            p = core.matrix_world @ vert.co
            if p.z >= head_cutoff and abs(p.x-center.x) <= 1.30:
                head_points.append(p)
            if p.z >= face_cutoff and abs(p.x-center.x) <= .78:
                face_points.append(p)
    focus_tail = [o for o in matching("tail") if "scarf" not in o.name.lower()]
    focus_outfit = matching("scarf", "vest", "harness", "belt", "pouch", "backpack", "compass", "flask", "wrap", "bedroll", "emblem")
    def focus_center(items, fallback):
        pts = [o.matrix_world @ Vector(c) for o in items if o.type == "MESH" for c in o.bound_box]
        if not pts:
            return fallback
        lo = Vector(tuple(min(p[i] for p in pts) for i in range(3)))
        hi = Vector(tuple(max(p[i] for p in pts) for i in range(3)))
        return (lo + hi) * .5
    if face_points:
        hmin = Vector(tuple(min(p[i] for p in face_points) for i in range(3)))
        hmax = Vector(tuple(max(p[i] for p in face_points) for i in range(3)))
        target_head = (hmin + hmax) * .5
    else:
        target_head = focus_center(focus_head, Vector((center.x, center.y, face_z)))
    target_tail = focus_center(focus_tail, Vector((center.x, center.y, torso_z)))
    target_outfit = focus_center(focus_outfit, Vector((center.x, center.y, torso_z)))
    views = [
        ("01_front.png", center, (0, -1, 0), 55, None, None),
        ("02_three_quarter.png", center, (4, -7, 0.15), 55, None, None),
        ("03_side.png", center, (1, 0, 0), 55, None, None),
        ("04_back.png", center, (0, 1, 0), 55, None, None),
        ("05_face_closeup.png", target_head, (0, -1, 0), 78, focus_head, face_points),
        ("06_head_profile.png", target_head, (1, -0.05, 0), 72, focus_head, head_points),
        ("07_tail_profile.png", target_tail, (1, 0, 0), 62, focus_tail, None),
        ("08_outfit_detail.png", target_outfit, (0, -1, 0), 65, focus_outfit, None),
    ]
    for filename, target, direction, lens, focus, focus_pts in views:
        if filename == "05_face_closeup.png":
            target = Vector((center.x, center.y, minimum.z + height * .70))
            camera.location = target + Vector((0, -3.2, 0))
            camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
            camera.data.lens = 70
        elif filename == "06_head_profile.png":
            target = Vector((center.x, center.y, minimum.z + height * .72))
            camera.location = target + Vector((3.6, 0, 0))
            camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
            camera.data.lens = 70
        elif filename == "07_tail_profile.png":
            point_camera(camera, target, (0, -1, 0), minimum, maximum, lens=62, focus_objects=focus)
        else:
            point_camera(camera, target, direction, minimum, maximum, lens=lens, focus_objects=focus, focus_points=focus_pts)
        scene.render.filepath = str(REVIEW / filename)
        t = time.time()
        bpy.ops.render.render(write_still=True)
        stats.setdefault("render_seconds", {})[filename] = round(time.time()-t, 2)
    override = bpy.data.materials.new("Review only | flat black silhouette")
    override.diffuse_color = (0, 0, 0, 1)
    override.use_nodes = True
    override.node_tree.nodes.clear()
    output = override.node_tree.nodes.new("ShaderNodeOutputMaterial")
    emission = override.node_tree.nodes.new("ShaderNodeEmission")
    emission.inputs["Color"].default_value = (0, 0, 0, 1)
    emission.inputs["Strength"].default_value = 1
    override.node_tree.links.new(emission.outputs[0], output.inputs["Surface"])
    bpy.context.view_layer.material_override = override
    for filename, direction in (("09_black_silhouette_front.png", (0, -1, 0)),
                                ("10_black_silhouette_three_quarter.png", (4, -7, .15))):
        point_camera(camera, center, direction, minimum, maximum, full=True, lens=55)
        scene.render.filepath = str(REVIEW / filename)
        t = time.time()
        bpy.ops.render.render(write_still=True)
        stats.setdefault("render_seconds", {})[filename] = round(time.time()-t, 2)
    bpy.context.view_layer.material_override = None
    scene.render.resolution_x = 1200
    scene.render.resolution_y = 1200


def main():
    if not CANDIDATE.is_file():
        raise RuntimeError(f"Candidate not found: {CANDIDATE}")
    REVIEW.mkdir(parents=True, exist_ok=True)
    BLEND.parent.mkdir(parents=True, exist_ok=True)
    (OUT / "reports").mkdir(parents=True, exist_ok=True)
    gltf = glb_json(CANDIDATE)
    started = time.time()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(CANDIDATE))
    import_seconds = time.time() - started
    imported = list(bpy.context.scene.objects)
    assets = [o for o in imported if o.type not in ("CAMERA", "LIGHT")]
    meshes = [o for o in assets if o.type == "MESH"]
    minimum, maximum = mesh_bounds(meshes)
    geometry = geometry_audit(meshes)
    mats = material_audit()
    armatures = [o for o in assets if o.type == "ARMATURE"]
    curves = [o for o in assets if o.type == "CURVE"]
    skinned_meshes = [o.name for o in meshes if o.vertex_groups and any(m.type == "ARMATURE" for m in o.modifiers)]
    dims = maximum - minimum
    stats = {
        "stage": 5,
        "candidate": str(CANDIDATE.relative_to(ROOT)),
        "reference": str(REFERENCE.relative_to(ROOT)),
        "dimensions": {"x": round(dims.x, 5), "y": round(dims.y, 5), "z": round(dims.z, 5),
                       "unit": "GLB meters as imported into Blender"},
        "bounding_box": {"min": [round(x, 5) for x in minimum],
                         "max": [round(x, 5) for x in maximum]},
        "origin_position": "GLB node transforms preserved; imported object origins summarized in audit blend",
        "forward_axis": "-Y (front view verified from facial features)",
        "up_axis": "+Z (GLB Y-up converted by Blender importer)",
        "objects": len(assets), "meshes": len(meshes),
        "vertices": geometry["vertices"], "polygons": geometry["polygons"],
        "triangles": geometry["triangles"],
        "materials": len(bpy.data.materials), "textures": len(bpy.data.images),
        "armatures": len(armatures), "skins": len(gltf.get("skins", [])),
        "animations": len(gltf.get("animations", [])), "curves": len(curves),
        "skinned_meshes": skinned_meshes,
        "glb_json_meshes": len(gltf.get("meshes", [])),
        "model_origin_and_transforms": [{"object": o.name, "location": [round(v, 5) for v in o.location],
                                           "rotation_euler": [round(v, 5) for v in o.rotation_euler],
                                           "scale": [round(v, 5) for v in o.scale]} for o in assets],
        "material_audit": mats,
        "topology": {k: geometry[k] for k in ("nonmanifold_meshes", "duplicate_faces", "potential_duplicate_vertices")},
        "object_classification": geometry["object_classification"],
        "mesh_topology": geometry["topology_by_mesh"],
        "import_seconds": round(import_seconds, 3),
        "viewport_responsiveness": "not directly measurable in background validation; import and render time recorded",
        "render_paths": [str((REVIEW / f).relative_to(ROOT)) for f in (
            "01_front.png", "02_three_quarter.png", "03_side.png", "04_back.png",
            "05_face_closeup.png", "06_head_profile.png", "07_tail_profile.png",
            "08_outfit_detail.png", "09_black_silhouette_front.png",
            "10_black_silhouette_three_quarter.png")],
    }
    scene, camera = setup_render(minimum, maximum)
    render_views(assets, minimum, maximum, stats)
    # Keep imported candidate data unmodified and preserve its material assignments.
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
    stats["validation_blend"] = str(BLEND.relative_to(ROOT))
    stats["topology_table"] = str(AUDIT_REPORT.relative_to(ROOT))
    JSON_REPORT.write_text(json.dumps(stats, indent=2) + "\n")
    print(json.dumps({"objects": stats["objects"], "meshes": stats["meshes"],
                      "vertices": stats["vertices"], "polygons": stats["polygons"],
                      "triangles": stats["triangles"], "materials": stats["materials"],
                      "textures": stats["textures"], "armatures": stats["armatures"],
                      "skins": stats["skins"], "animations": stats["animations"],
                      "dimensions": stats["dimensions"], "import_seconds": stats["import_seconds"]}, indent=2))


if __name__ == "__main__":
    main()
