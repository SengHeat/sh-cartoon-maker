#!/usr/bin/env python3
"""Build a rig-ready KIKO blockout and render a four-view turnaround.

Run from a terminal with:
    blender --background --python build_kiko.py

The script is deliberately self-contained and idempotent.  It removes the
current scene contents before rebuilding, but does not save a .blend file.
"""

from pathlib import Path
import math
import bpy
import bmesh
from mathutils import Vector


# -----------------------------------------------------------------------------
# Artist-facing controls
# -----------------------------------------------------------------------------

CONFIG = {
    "proportions": {
        "character_height": 3.55,
        "head_center_z": 2.70,
        "head_scale": (0.72, 0.59, 0.66),
        "torso_center_z": 1.55,
        "torso_scale": (0.48, 0.32, 0.70),
        "shoulder_width": 1.16,
        "arm_length": 0.80,
        "upper_arm_ratio": 0.53,
        "shoulder_radius": 0.19,
        "elbow_radius": 0.145,
        "wrist_radius": 0.095,
        "leg_length": 0.87,
        "ear_length": 1.02,
        "ear_width": 0.55,
        "tail_length": 1.95,
        "tail_thickness": 0.33,
        "tail_root_height": 1.35,
        "tail_bone_count": 5,
        # Tail color bands: (segment_index, material_slot).  Segment i spans
        # tail_centers[i] to tail_centers[i+1].  Slots: 0=teal, 1=orange, 2=cream.
        # Unlisted segments default to teal.
        "tail_bands": [(2, 1), (3, 2), (4, 1)],
        "harness_surface_offset": 0.008,
    },
    "colors": {
        "body_teal": (0.105, 0.255, 0.270, 1.0),
        "fur_cream": (0.76, 0.63, 0.43, 1.0),
        "orange_accent": (0.80, 0.245, 0.075, 1.0),
        "ear_inner": (0.92, 0.40, 0.30, 1.0),
        "leather_brown": (0.20, 0.075, 0.025, 1.0),
        "eye_white": (0.86, 0.82, 0.70, 1.0),
        "iris_brown": (0.42, 0.115, 0.025, 1.0),
        "eye_dark": (0.008, 0.006, 0.005, 1.0),
        "nose": (0.36, 0.095, 0.085, 1.0),
        "studio_floor": (0.075, 0.082, 0.090, 1.0),
        "world_background": (0.018, 0.022, 0.028, 1.0),
    },
    "subdiv_level": 2,
    "render_samples": 48,
    "resolution": 1080,
    "output_dir": "renders",
    "camera_lens_mm": 66,
    "generate_weights": True,
    "weight_falloff_power": 3.0,
}

BUILD_STATUS = {
    "shade_smooth_applied": False,
    "loft_normals_recalculated": False,
    "background_node_color_set": False,
    "total_vertex_group_count": 0,
    "deform_group_count_per_mesh": 0,
    "outfit_curves_skinned": 0,
    "hierarchy_preserved": False,
    "tail_bands_from_config": False,
}


# -----------------------------------------------------------------------------
# Scene and material helpers
# -----------------------------------------------------------------------------

def clean_scene():
    """Remove every object and orphaned data block for repeatable rebuilds."""
    bpy.ops.object.mode_set(mode="OBJECT") if bpy.context.object and bpy.context.object.mode != "OBJECT" else None
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.armatures,
                       bpy.data.materials, bpy.data.cameras, bpy.data.lights):
        for block in list(datablocks):
            if block.users == 0:
                datablocks.remove(block)


def make_collection(name, parent=None):
    coll = bpy.data.collections.new(name)
    (parent.children if parent else bpy.context.scene.collection.children).link(coll)
    return coll


def move_to_collection(obj, collection):
    for old in list(obj.users_collection):
        old.objects.unlink(obj)
    collection.objects.link(obj)


def make_empty(name, location, collection, parent=None):
    obj = bpy.data.objects.new(name, None)
    obj.empty_display_type = "PLAIN_AXES"
    obj.empty_display_size = 0.16
    obj.location = location
    collection.objects.link(obj)
    obj.parent = parent
    return obj


def make_material(name, color, roughness=0.86, metallic=0.0, specular=0.28):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    # Blender 4/5 names this socket "Specular IOR Level".
    socket = bsdf.inputs.get("Specular IOR Level") or bsdf.inputs.get("Specular")
    if socket:
        socket.default_value = specular
    return mat


def finish_mesh(obj, material, subdiv=True):
    if material:
        obj.data.materials.append(material)
    obj.data.shade_smooth()
    BUILD_STATUS["shade_smooth_applied"] = True
    if subdiv and CONFIG["subdiv_level"] > 0:
        mod = obj.modifiers.new("Subdivision Surface", "SUBSURF")
        mod.subdivision_type = "CATMULL_CLARK"
        mod.levels = min(CONFIG["subdiv_level"], 2)
        mod.render_levels = CONFIG["subdiv_level"]
    return obj


def uv_form(name, location, scale, material, collection, parent=None,
            segments=32, rings=20, rotation=(0, 0, 0)):
    """Create a quad-dominant UV-sphere form."""
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=segments, ring_count=rings, location=location, rotation=rotation
    )
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    finish_mesh(obj, material)
    move_to_collection(obj, collection)
    obj.parent = parent
    return obj


def tapered_form(name, start, end, radius_a, radius_b, material, collection,
                 parent=None, vertices=24):
    """A tapered, rounded limb section aligned between two points."""
    start, end = Vector(start), Vector(end)
    midpoint = (start + end) * 0.5
    length = (end - start).length
    bpy.ops.mesh.primitive_cone_add(
        vertices=vertices, radius1=radius_b, radius2=radius_a,
        depth=length, end_fill_type="NGON", location=midpoint,
    )
    obj = bpy.context.object
    obj.name = name
    obj.rotation_euler = (end - start).to_track_quat("Z", "Y").to_euler()
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    # Bevel softens the capped ends before subdivision.
    bevel = obj.modifiers.new("Soft form", "BEVEL")
    bevel.width = min(radius_a, radius_b) * 0.35
    bevel.segments = 3
    finish_mesh(obj, material)
    move_to_collection(obj, collection)
    obj.parent = parent
    return obj


def loft_mesh(name, centers, radii, material, collection, parent=None, sides=24):
    """Build a quad strip along a 3D path; used for ears, tail, and fur clumps."""
    verts, faces = [], []
    centers = [Vector(c) for c in centers]
    for i, center in enumerate(centers):
        before = centers[max(0, i - 1)]
        after = centers[min(len(centers) - 1, i + 1)]
        tangent = (after - before).normalized()
        normal = tangent.cross(Vector((0, 1, 0)))
        if normal.length < 0.01:
            normal = tangent.cross(Vector((1, 0, 0)))
        normal.normalize()
        binormal = tangent.cross(normal).normalized()
        rx, ry = radii[i]
        for j in range(sides):
            angle = math.tau * j / sides
            verts.append(center + normal * (math.cos(angle) * rx) +
                         binormal * (math.sin(angle) * ry))
    faces.append(tuple(reversed(range(sides))))
    for i in range(len(centers) - 1):
        for j in range(sides):
            a = i * sides + j
            b = i * sides + (j + 1) % sides
            faces.append((a, b, b + sides, a + sides))
    faces.append(tuple(range((len(centers) - 1) * sides, len(centers) * sides)))
    mesh = bpy.data.meshes.new(name + "_Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    BUILD_STATUS["loft_normals_recalculated"] = True
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    finish_mesh(obj, material)
    obj.parent = parent
    return obj


def make_curve(name, points, bevel, material, collection, parent=None, cyclic=False):
    data = bpy.data.curves.new(name + "_Curve", "CURVE")
    data.dimensions = "3D"
    data.resolution_u = 12
    data.bevel_depth = bevel
    data.bevel_resolution = 4
    spline = data.splines.new("BEZIER")
    spline.bezier_points.add(len(points) - 1)
    for bp, point in zip(spline.bezier_points, points):
        bp.co = point
        bp.handle_left_type = bp.handle_right_type = "AUTO"
    spline.use_cyclic_u = cyclic
    obj = bpy.data.objects.new(name, data)
    collection.objects.link(obj)
    data.materials.append(material)
    obj.parent = parent
    return obj


# -----------------------------------------------------------------------------
# Character construction
# -----------------------------------------------------------------------------

def build_character(materials):
    p = CONFIG["proportions"]
    root_collection = make_collection("KIKO_BLOCKOUT")
    geo_collection = make_collection("KIKO_GEO", root_collection)
    rig_collection = make_collection("KIKO_RIG_PLACEHOLDER", root_collection)
    controls_collection = make_collection("KIKO_ORGANIZATION", root_collection)

    root = make_empty("KIKO_ROOT", (0, 0, 0), controls_collection)
    body_group = make_empty("BODY_PARTS", (0, 0, 0), controls_collection, root)
    head_group = make_empty("HEAD_PARTS", (0, 0, 0), controls_collection, root)
    tail_group = make_empty("TAIL_PARTS", (0, 0, 0), controls_collection, root)
    outfit_group = make_empty("OUTFIT_PARTS", (0, 0, 0), controls_collection, root)

    teal, cream = materials["teal"], materials["cream"]

    # Compact body and belly.
    uv_form("KIKO_Torso", (0, 0, p["torso_center_z"]), p["torso_scale"],
            teal, geo_collection, body_group)
    uv_form("KIKO_Belly", (0, -0.294, 1.49), (0.29, 0.055, 0.47),
            cream, geo_collection, body_group)

    # Broad, slightly flattened head and integrated cream lower-face shapes.
    uv_form("KIKO_Head", (0, 0, p["head_center_z"]), p["head_scale"],
            teal, geo_collection, head_group)
    uv_form("KIKO_FaceMask", (0, -0.535, 2.70), (0.50, 0.075, 0.39),
            cream, geo_collection, head_group)
    uv_form("KIKO_Muzzle", (0, -0.625, 2.48), (0.31, 0.12, 0.19),
            cream, geo_collection, head_group)
    uv_form("KIKO_Nose", (0, -0.747, 2.56), (0.075, 0.042, 0.055),
            materials["nose"], geo_collection, head_group, segments=24, rings=16)

    # Large eyes, brown irises, pupils, and small catchlights.
    for side, x in (("L", 0.245), ("R", -0.245)):
        uv_form(f"KIKO_Eye.{side}", (x, -0.585, 2.80), (0.205, 0.105, 0.245),
                materials["eye_white"], geo_collection, head_group)
        uv_form(f"KIKO_Iris.{side}", (x, -0.686, 2.79), (0.118, 0.022, 0.145),
                materials["iris"], geo_collection, head_group, segments=24, rings=16)
        uv_form(f"KIKO_Pupil.{side}", (x, -0.708, 2.79), (0.058, 0.014, 0.090),
                materials["eye_dark"], geo_collection, head_group, segments=20, rings=12)
        uv_form(f"KIKO_EyeHighlight.{side}", (x - 0.025, -0.724, 2.855),
                (0.020, 0.007, 0.026), materials["eye_white"], geo_collection,
                head_group, segments=16, rings=10)

    # Broad pointed fennec ears. Inner ears are inset volumes, not flat planes.
    for side, sign in (("L", 1), ("R", -1)):
        root_x = sign * 0.50
        ear_centers = [(root_x, 0.01, 2.98),
                       (sign * 0.79, 0.015, 3.20),
                       (sign * 1.06, 0.02, 3.40),
                       (sign * 1.19, 0.03, 3.55)]
        ear_radii = [(0.26, 0.16), (0.30, 0.17), (0.20, 0.13), (0.035, 0.025)]
        loft_mesh(f"KIKO_Ear.{side}", ear_centers, ear_radii, teal,
                  geo_collection, head_group, sides=24)
        inner_centers = [(x, y - 0.15, z) for x, y, z in ear_centers[:-1]]
        inner_radii = [(0.14, 0.035), (0.19, 0.042), (0.08, 0.025)]
        loft_mesh(f"KIKO_InnerEar.{side}", inner_centers, inner_radii,
                  materials["inner_ear"], geo_collection, head_group, sides=20)

    # Separate mohawk tuft, made from overlapping curved quad lofts.
    for i, (x, lean, height, width) in enumerate([
        (-0.29, -0.15, 0.40, 0.14), (-0.18, -0.12, 0.55, 0.16),
        (-0.06, -0.06, 0.68, 0.18), (0.07, 0.04, 0.63, 0.17),
        (0.19, 0.10, 0.52, 0.15), (0.29, 0.14, 0.38, 0.13),
    ]):
        z = 3.18
        loft_mesh(
            f"KIKO_Mohawk_{i:02d}",
            [(x, 0.02, z), (x + lean * 0.25, 0.01, z + height * 0.40),
             (x + lean, 0.0, z + height)],
            [(width, width * 0.68), (width * 0.75, width * 0.52), (0.025, 0.018)],
            materials["orange" if i in (2, 3) else "teal"], geo_collection,
            head_group, sides=18,
        )

    # T-pose arms. Length is 15% shorter than the first blockout and the radius
    # falls strongly from shoulder to wrist.
    for side, sign in (("L", 1), ("R", -1)):
        shoulder = (sign * 0.47, 0, 1.91)
        arm_length = p["arm_length"]
        elbow_x = 0.47 + arm_length * p["upper_arm_ratio"]
        wrist_x = 0.47 + arm_length
        elbow = (sign * elbow_x, 0, 1.89)
        wrist = (sign * wrist_x, 0, 1.87)
        tapered_form(f"KIKO_UpperArm.{side}", shoulder, elbow,
                     p["shoulder_radius"], p["elbow_radius"],
                     teal, geo_collection, body_group)
        tapered_form(f"KIKO_Forearm.{side}", elbow, wrist,
                     p["elbow_radius"], p["wrist_radius"],
                     teal, geo_collection, body_group)
        palm_x = wrist_x + 0.13
        uv_form(f"KIKO_Hand.{side}", (sign * palm_x, -0.01, 1.87),
                (0.19, 0.16, 0.18), teal, geo_collection, body_group)
        # Three small digit pads make the silhouette read as a paw, not a mitten.
        for toe in range(3):
            uv_form(f"KIKO_Finger{toe+1}.{side}",
                    (sign * (palm_x + 0.12 + toe * 0.018), -0.11 + toe * 0.11, 1.86),
                    (0.085, 0.050, 0.058), cream, geo_collection, body_group,
                    segments=20, rings=12)

    # Short sturdy legs and broad three-toe feet.
    for side, sign in (("L", 1), ("R", -1)):
        hip = (sign * 0.23, 0, 1.10)
        knee = (sign * 0.25, 0.02, 0.69)
        ankle = (sign * 0.26, -0.02, 0.31)
        tapered_form(f"KIKO_Thigh.{side}", hip, knee, 0.24, 0.20,
                     teal, geo_collection, body_group)
        tapered_form(f"KIKO_Shin.{side}", knee, ankle, 0.20, 0.16,
                     teal, geo_collection, body_group)
        uv_form(f"KIKO_Foot.{side}", (sign * 0.26, -0.20, 0.18),
                (0.27, 0.37, 0.16), teal, geo_collection, body_group)
        for toe in range(3):
            x = sign * (0.12 + toe * 0.14)
            uv_form(f"KIKO_Toe{toe+1}.{side}", (x, -0.51, 0.15),
                    (0.09, 0.13, 0.075), cream, geo_collection, body_group,
                    segments=20, rings=12)

    # Big swept fluffy tail with alternating accent bands and extra silhouette clumps.
    root_z = p["tail_root_height"]
    # The first two sections overlap the rump, visually welding the tail to the back.
    tail_centers = [(0, 0.20, root_z), (0, 0.43, 1.13), (0, 0.72, 0.94),
                    (0, 1.05, 0.91), (0, 1.35, 1.08), (0, 1.55, 1.37)]
    tail_radii = [(0.25, 0.22), (0.36, 0.31), (0.43, 0.36),
                  (0.39, 0.33), (0.28, 0.24), (0.055, 0.045)]
    tail = loft_mesh("KIKO_FluffyTail", tail_centers, tail_radii, teal,
                     geo_collection, tail_group, sides=28)
    tail.data.materials.append(materials["orange"])
    tail.data.materials.append(cream)
    # Assign bands from CONFIG — segment boundaries derived from tail_centers.
    band_map = dict(CONFIG["proportions"]["tail_bands"])
    for poly in tail.data.polygons:
        cy = sum(tail.data.vertices[v].co.y for v in poly.vertices) / len(poly.vertices)
        if len(poly.vertices) > 4:
            # Cap face (N-gon at ring endpoints): always teal.
            poly.material_index = 0
            continue
        seg_idx = len(tail_centers) - 2
        for i in range(len(tail_centers) - 1):
            if cy < tail_centers[i + 1][1]:
                seg_idx = i
                break
        poly.material_index = band_map.get(seg_idx, 0)
    BUILD_STATUS["tail_bands_from_config"] = True
    for i, (y, z, sign) in enumerate([(0.67, 0.78, 1), (0.84, 0.77, -1),
                                       (1.08, 0.83, 1), (1.28, 1.00, -1)]):
        loft_mesh(f"KIKO_TailFluff_{i:02d}", [(0, y, z),
                  (sign * 0.28, y + 0.07, z + 0.08)],
                  [(0.16, 0.12), (0.025, 0.018)], teal, geo_collection,
                  tail_group, sides=16)
    uv_form("KIKO_TailRootBlend", (0, 0.25, root_z), (0.31, 0.25, 0.28),
            teal, geo_collection, tail_group)

    # Simple adventurer outfit: vest, belt, shoulder straps, scarf, and backpack.
    uv_form("KIKO_Vest", (0, -0.015, 1.55), (0.50, 0.335, 0.55),
            materials["leather"], geo_collection, outfit_group)
    make_curve("KIKO_Scarf", [(-0.32, 0, 2.10), (0, -0.37, 2.05),
                               (0.32, 0, 2.10), (0, 0.25, 2.12)],
               0.085, materials["orange"], geo_collection, outfit_group, cyclic=True)
    make_curve("KIKO_Belt", [(-0.42, 0, 1.21), (0, -0.34, 1.19),
                              (0.42, 0, 1.21), (0, 0.28, 1.22)],
               0.045, materials["leather"], geo_collection, outfit_group, cyclic=True)
    harness_y = -0.326 - p["harness_surface_offset"]
    for side, sign in (("L", 1), ("R", -1)):
        make_curve(f"KIKO_ShoulderStrap.{side}",
                   [(sign * 0.31, harness_y + 0.030, 1.93),
                    (sign * 0.24, harness_y - 0.005, 1.70),
                    (sign * 0.17, harness_y - 0.012, 1.45),
                    (sign * 0.10, harness_y + 0.018, 1.20)],
                   0.032, materials["leather"], geo_collection, outfit_group)
    uv_form("KIKO_Backpack", (0, 0.36, 1.57), (0.38, 0.22, 0.48),
            materials["leather"], geo_collection, outfit_group)

    armature = build_armature(rig_collection)
    armature.parent = root
    prepare_skinning(geo_collection, armature)
    return root, armature


# -----------------------------------------------------------------------------
# Unskinned metarig placeholder
# -----------------------------------------------------------------------------

def build_armature(collection):
    data = bpy.data.armatures.new("KIKO_MetarigPlaceholder")
    arm = bpy.data.objects.new("KIKO_MetarigPlaceholder", data)
    collection.objects.link(arm)
    arm.show_in_front = True
    arm.display_type = "WIRE"
    bpy.context.view_layer.objects.active = arm
    arm.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")

    def bone(name, head, tail, parent=None, connected=False):
        b = data.edit_bones.new(name)
        b.head, b.tail = head, tail
        b.parent = parent
        b.use_connect = connected and parent is not None
        return b

    root = bone("root", (0, 0, 0), (0, 0, 0.28))
    root.use_deform = False
    pelvis = bone("pelvis", (0, 0, 0.82), (0, 0, 1.18), root)
    spine1 = bone("spine", (0, 0, 1.18), (0, 0, 1.62), pelvis, True)
    chest = bone("chest", (0, 0, 1.62), (0, 0, 1.94), spine1, True)
    neck = bone("neck", (0, 0, 1.94), (0, 0, 2.25), chest, True)
    head = bone("head", (0, 0, 2.25), (0, 0, 3.05), neck, True)
    p = CONFIG["proportions"]
    for side, sign in (("L", 1), ("R", -1)):
        clav = bone(f"clavicle.{side}", (0, 0, 1.90), (sign * 0.46, 0, 1.91), chest)
        elbow_x = 0.47 + p["arm_length"] * p["upper_arm_ratio"]
        wrist_x = 0.47 + p["arm_length"]
        upper = bone(f"upper_arm.{side}", clav.tail, (sign * elbow_x, 0, 1.89), clav, True)
        lower = bone(f"forearm.{side}", upper.tail, (sign * wrist_x, 0, 1.87), upper, True)
        bone(f"hand.{side}", lower.tail, (sign * (wrist_x + .27), 0, 1.87), lower, True)
        thigh = bone(f"thigh.{side}", (sign * 0.22, 0, 1.10), (sign * 0.25, 0.02, 0.69), pelvis)
        shin = bone(f"shin.{side}", thigh.tail, (sign * 0.26, -0.02, 0.31), thigh, True)
        bone(f"foot.{side}", shin.tail, (sign * 0.26, -0.46, 0.14), shin, True)
        bone(f"ear.{side}", (sign * 0.48, 0, 3.00), (sign * 1.14, 0.03, 3.52), head)
    tail_parent = pelvis
    tail_count = max(1, int(p["tail_bone_count"]))
    control_points = [Vector(v) for v in [(0, .20, p["tail_root_height"]), (0, .43, 1.13),
                      (0, .72, .94), (0, 1.05, .91), (0, 1.35, 1.08), (0, 1.55, 1.37)]]
    # Resample the visual tail path to exactly CONFIG tail bones.
    distances = [0.0]
    for a, b in zip(control_points, control_points[1:]):
        distances.append(distances[-1] + (b - a).length)
    sampled = []
    for i in range(tail_count + 1):
        wanted = distances[-1] * i / tail_count
        seg = next(
            (j for j in range(len(distances) - 1) if distances[j + 1] >= wanted),
            len(distances) - 2,
        )
        fac = (wanted - distances[seg]) / max(distances[seg + 1] - distances[seg], 1e-8)
        sampled.append(control_points[seg].lerp(control_points[seg + 1], fac))
    for i in range(tail_count):
        tail_parent = bone(f"tail.{i+1:03d}", sampled[i], sampled[i+1],
                           tail_parent, i > 0)
    bpy.ops.object.mode_set(mode="OBJECT")
    arm.hide_render = True
    arm.hide_set(True)  # Available in the .blend, invisible in beauty renders.
    return arm


def point_segment_distance(point, start, end):
    """Shortest distance from point to a bone segment."""
    segment = end - start
    length_sq = segment.length_squared
    if length_sq < 1e-10:
        return (point - start).length
    factor = max(0.0, min(1.0, (point - start).dot(segment) / length_sq))
    return (point - (start + segment * factor)).length


def prepare_skinning(geo_collection, armature):
    """Add exact-name deform groups and optional deterministic proximity weights.

    KIKO remains a multipart blockout, so every mesh part receives the same
    deform-group schema.  This makes individual pieces immediately usable in
    weight-paint tests without joining or destructively applying modifiers.

    Outfit curves are converted to mesh before skinning so they receive the
    same proximity-weight pipeline as the body parts (chosen over adding
    Armature modifiers to curves directly for uniform weight assignment).
    """
    # Convert outfit curves to mesh for uniform weight assignment.
    armature.select_set(False)
    curves_to_convert = [obj for obj in geo_collection.all_objects
                         if obj.type == "CURVE" and obj.name.startswith("KIKO_")]
    for obj in curves_to_convert:
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.convert(target="MESH")
    BUILD_STATUS["outfit_curves_skinned"] = len(curves_to_convert)

    tail_names = [f"tail.{i:03d}" for i in range(1, int(CONFIG["proportions"]["tail_bone_count"]) + 1)]
    group_names = [
        "pelvis", "spine", "chest", "neck", "head", "clavicle.L", "clavicle.R",
        "upper_arm.L", "upper_arm.R", "forearm.L", "forearm.R",
        "hand.L", "hand.R", "thigh.L", "thigh.R", "shin.L", "shin.R",
        "foot.L", "foot.R", "ear.L", "ear.R",
    ] + tail_names
    BUILD_STATUS["deform_group_count_per_mesh"] = len(group_names)
    bone_segments = {}
    for name in group_names:
        bone = armature.data.bones.get(name)
        if bone:
            bone_segments[name] = (armature.matrix_world @ bone.head_local,
                                   armature.matrix_world @ bone.tail_local)

    for obj in list(geo_collection.all_objects):
        if obj.type != "MESH" or not obj.name.startswith("KIKO_"):
            continue
        groups = {}
        for name in group_names:
            old = obj.vertex_groups.get(name)
            groups[name] = old or obj.vertex_groups.new(name=name)

        if CONFIG["generate_weights"] and bone_segments:
            power = float(CONFIG["weight_falloff_power"])
            for vertex in obj.data.vertices:
                world_point = obj.matrix_world @ vertex.co
                ranked = sorted(
                    (point_segment_distance(world_point, a, b), name)
                    for name, (a, b) in bone_segments.items()
                )[:4]
                raw = [1.0 / max(distance, 0.035) ** power for distance, _ in ranked]
                total = sum(raw)
                for weight, (_, name) in zip(raw, ranked):
                    groups[name].add([vertex.index], weight / total, "REPLACE")

        # Armature modifier handles deformation; no re-parenting so the
        # organizational empties (BODY_PARTS, HEAD_PARTS, etc.) keep their children.
        modifier = obj.modifiers.get("Armature Deform") or obj.modifiers.new("Armature Deform", "ARMATURE")
        modifier.object = armature
        modifier.use_deform_preserve_volume = True

    BUILD_STATUS["hierarchy_preserved"] = not any(
        obj.parent == armature
        for obj in geo_collection.all_objects
        if obj.type == "MESH" and obj.name.startswith("KIKO_")
    )

    BUILD_STATUS["total_vertex_group_count"] = sum(
        len(obj.vertex_groups)
        for obj in geo_collection.all_objects
        if obj.type == "MESH" and obj.name.startswith("KIKO_")
    )


# -----------------------------------------------------------------------------
# Studio, camera, and turnaround rendering
# -----------------------------------------------------------------------------

def setup_studio(materials):
    studio = make_collection("KIKO_STUDIO")
    bpy.ops.mesh.primitive_plane_add(size=20, location=(0, 0, 0))
    floor = bpy.context.object
    floor.name = "StudioFloor"
    floor.data.materials.append(materials["floor"])
    move_to_collection(floor, studio)

    scene = bpy.context.scene
    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes["Background"]
    background.inputs["Color"].default_value = CONFIG["colors"]["world_background"]
    BUILD_STATUS["background_node_color_set"] = all(
        abs(actual - expected) < 1e-6
        for actual, expected in zip(
            background.inputs["Color"].default_value,
            CONFIG["colors"]["world_background"],
        )
    )

    def area(name, location, energy, size, color, target=(0, 0, 1.8)):
        data = bpy.data.lights.new(name + "_Data", "AREA")
        data.energy, data.shape, data.size, data.color = energy, "DISK", size, color
        obj = bpy.data.objects.new(name, data)
        studio.objects.link(obj)
        obj.location = location
        obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()
        return obj

    area("Key_Warm", (-4.5, -5.0, 6.0), 1150, 5.0, (1.0, 0.78, 0.60))
    area("Fill_Cool", (4.5, -3.5, 4.0), 700, 5.5, (0.52, 0.68, 1.0))
    # Neutral rim prevents rear-facing teal fur from shifting olive under warm light.
    area("Rim_Neutral", (2.5, 4.0, 5.0), 900, 4.0, (0.78, 0.86, 1.0))

    cam_data = bpy.data.cameras.new("KIKO_TurnaroundCamera_Data")
    cam = bpy.data.objects.new("KIKO_TurnaroundCamera", cam_data)
    studio.objects.link(cam)
    cam.data.lens = CONFIG["camera_lens_mm"]
    scene.camera = cam
    return cam


def configure_render():
    scene = bpy.context.scene
    # Blender 5.2 accepts BLENDER_EEVEE; some 4.x builds expose the NEXT name.
    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = CONFIG["resolution"]
    scene.render.resolution_y = CONFIG["resolution"]
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.render.image_settings.color_mode = "RGBA"
    if hasattr(scene, "eevee") and hasattr(scene.eevee, "taa_render_samples"):
        scene.eevee.taa_render_samples = CONFIG["render_samples"]
    scene.view_settings.look = "AgX - Medium High Contrast"


def render_turnaround(camera):
    output = Path.cwd() / CONFIG["output_dir"]
    output.mkdir(parents=True, exist_ok=True)
    target = Vector((0, 0, 1.85))
    # Clockwise around KIKO: front, front 3/4, side, back.
    views = [
        (0.0, 6.8, 1.95),
        (45.0, 6.8, 2.00),
        (90.0, 6.8, 1.95),
        (180.0, 6.8, 1.95),
    ]
    scene = bpy.context.scene
    for index, (degrees, radius, z) in enumerate(views, start=1):
        angle = math.radians(degrees)
        camera.location = (math.sin(angle) * radius, -math.cos(angle) * radius, z)
        camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
        scene.render.filepath = str(output / f"kiko_{index:03d}.png")
        bpy.ops.render.render(write_still=True)


def main():
    clean_scene()
    c = CONFIG["colors"]
    materials = {
        "teal": make_material("MAT_BODY_FUR_TEAL", c["body_teal"], 0.94, specular=0.20),
        "cream": make_material("MAT_Fur_Cream", c["fur_cream"], 0.94, specular=0.20),
        "orange": make_material("MAT_OrangeAccent", c["orange_accent"], 0.88),
        "inner_ear": make_material("MAT_InnerEar", c["ear_inner"], 0.84),
        "leather": make_material("MAT_LeatherBrown", c["leather_brown"], 0.78),
        "eye_white": make_material("MAT_EyeWhite", c["eye_white"], 0.28, specular=0.48),
        "iris": make_material("MAT_IrisBrown", c["iris_brown"], 0.30, specular=0.46),
        "eye_dark": make_material("MAT_EyeDark", c["eye_dark"], 0.24, specular=0.50),
        "nose": make_material("MAT_Nose", c["nose"], 0.52),
        "floor": make_material("MAT_StudioFloor", c["studio_floor"], 0.90),
    }
    materials["teal"]["is_body_fur_material"] = True
    build_character(materials)
    camera = setup_studio(materials)
    configure_render()
    render_turnaround(camera)
    body_material_count = sum(bool(mat.get("is_body_fur_material", False)) for mat in bpy.data.materials)
    print("\n=== KIKO BUILD SUMMARY ===")
    print(f"Body-fur materials: {body_material_count} (expected 1)")
    print(f"Arm length used: {CONFIG['proportions']['arm_length']:.3f} Blender units")
    print(f"Tail bone count: {int(CONFIG['proportions']['tail_bone_count'])}")
    print(f"Weights generated: {bool(CONFIG['generate_weights'])}")
    print(f"Shade smooth applied: {'yes' if BUILD_STATUS['shade_smooth_applied'] else 'no'}")
    print(
        f"Total vertex-group count: {BUILD_STATUS['total_vertex_group_count']} "
        f"({BUILD_STATUS['deform_group_count_per_mesh']} deform groups per mesh)"
    )
    print(
        "Background node color set: "
        f"{'yes' if BUILD_STATUS['background_node_color_set'] else 'no'}"
    )
    print(
        "Loft-mesh normals recalculated: "
        f"{'yes' if BUILD_STATUS['loft_normals_recalculated'] else 'no'}"
    )
    print(f"Outfit curves skinned: {BUILD_STATUS['outfit_curves_skinned']}")
    print(f"Hierarchy preserved: {'yes' if BUILD_STATUS['hierarchy_preserved'] else 'no'}")
    print(f"Tail bands from config: {'yes' if BUILD_STATUS['tail_bands_from_config'] else 'no'}")
    print(f"Renders: {Path.cwd() / CONFIG['output_dir']}")


if __name__ == "__main__":
    main()
