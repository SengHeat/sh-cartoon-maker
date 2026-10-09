"""
Stage 5.1 — Iteration 2: Focused cheek + crest + silhouette refinement.
Opens V3 blend, makes targeted fixes, re-exports and re-renders.

Primary focus: CHEEKS must be dramatically wider and fluffier.
Secondary: Crest edge softening, overall silhouette polish.
"""
import bpy
import bmesh
import os
import math
import json
import random
from mathutils import Vector

random.seed(42)

PROJECT = "/Users/macbook/Automation-Workplace/cartoon-maker"
BLEND_V3 = os.path.join(PROJECT, "projects/characters/kiko/blends/master/KIKO_visual_stage5_v3.blend")
GLB_V3 = os.path.join(PROJECT, "assets/characters/kiko_final/source/KIKO_source_v3.glb")
OUT_DIR = os.path.join(PROJECT, "projects/characters/kiko/review/stage5_v3")

# ================================================================
# Load V3 blend
# ================================================================
print("=== Loading V3 blend ===")
bpy.ops.wm.open_mainfile(filepath=BLEND_V3)

# Remove render infrastructure from previous pass
for obj in list(bpy.data.objects):
    if obj.type in ('CAMERA', 'LIGHT', 'EMPTY') or obj.name == "GroundPlane":
        bpy.data.objects.remove(obj, do_unlink=True)

# Build obj map
obj_map = {}
for obj in bpy.data.objects:
    obj_map[obj.name] = obj

# Bounds
all_min = Vector((float('inf'),) * 3)
all_max = Vector((float('-inf'),) * 3)
for obj in bpy.data.objects:
    if obj.type == 'MESH':
        for v in obj.data.vertices:
            co = obj.matrix_world @ v.co
            for i in range(3):
                if co[i] < all_min[i]: all_min[i] = co[i]
                if co[i] > all_max[i]: all_max[i] = co[i]

center = (all_min + all_max) / 2
height = all_max.z - all_min.z
head_z = all_min.z + height * 0.78

print(f"Height: {height:.3f}, center: {center}")

# ================================================================
# ITERATION 2 FIX 1 — DRAMATICALLY EXPAND CHEEKS
# ================================================================
print("\n=== ITER2: Expanding cheeks dramatically ===")

# The iter1 cheek masses were too small. The reference cheeks extend
# nearly as wide as the ears. We need to:
# 1. Further scale up existing cheek tufts
# 2. Further expand cheek/muzzle mesh
# 3. Make the iter1 cheek fur masses much bigger
# 4. Add more overlapping layers for volume

# Scale up iter1 cheek tufts even more
for name in ["KIKO | cheek tuft L 1", "KIKO | cheek tuft L 2", "KIKO | cheek tuft L 3",
             "KIKO | cheek tuft R 1", "KIKO | cheek tuft R 2", "KIKO | cheek tuft R 3"]:
    obj = obj_map.get(name)
    if obj:
        me = obj.data
        bm = bmesh.new()
        bm.from_mesh(me)
        c = sum((v.co.copy() for v in bm.verts), Vector((0,0,0))) / len(bm.verts)
        for v in bm.verts:
            offset = v.co - c
            v.co = c + Vector((offset.x * 1.4, offset.y * 1.3, offset.z * 1.4))
        bm.to_mesh(me)
        bm.free()
        me.update()
        print(f"  Further scaled: {name}")

# Further expand cheek/muzzle mesh at sides
cheek_muzzle = obj_map.get("KIKO | integrated cream cheeks and muzzle")
if cheek_muzzle:
    me = cheek_muzzle.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.normal_update()

    for v in bm.verts:
        world_co = cheek_muzzle.matrix_world @ v.co
        z_rel = (world_co.z - (head_z - 0.5)) / 1.0

        if 0.05 < z_rel < 0.85:
            x_offset = world_co.x - center.x
            if abs(x_offset) > 0.12:
                lateral_factor = min(abs(x_offset) / 0.4, 1.0) * 0.10
                sign = 1 if x_offset > 0 else -1
                local_dir = cheek_muzzle.matrix_world.inverted().to_3x3() @ Vector((sign, 0, 0))
                v.co += local_dir * lateral_factor

            # Forward push
            if v.normal.length > 0.001:
                v.co += v.normal * 0.025

    bm.to_mesh(me)
    bm.free()
    me.update()
    print("  Further expanded cheek/muzzle mesh")

# Scale up iter1 cheek fur masses significantly
for name_prefix in ["KIKO | cheek fur mass", "KIKO | cheek edge tuft"]:
    for obj_name, obj in list(obj_map.items()):
        if obj_name.startswith(name_prefix) and obj.type == 'MESH':
            me = obj.data
            bm = bmesh.new()
            bm.from_mesh(me)
            c = sum((v.co.copy() for v in bm.verts), Vector((0,0,0))) / len(bm.verts)
            for v in bm.verts:
                offset = v.co - c
                v.co = c + Vector((offset.x * 1.6, offset.y * 1.5, offset.z * 1.5))
            bm.to_mesh(me)
            bm.free()
            me.update()

            # Also push outward from character center
            obj_center = Vector((0,0,0))
            for v in obj.data.vertices:
                obj_center += obj.matrix_world @ v.co
            obj_center /= len(obj.data.vertices)
            push_dir = (obj_center - center).normalized()
            push_dir.z *= 0.3  # mostly lateral
            obj.location += push_dir * 0.06
            print(f"  Enlarged + pushed: {obj_name}")

# Add a second ring of even larger overlapping cheek masses
# These are the "hero" cheek shapes that define the silhouette
cream_mat = bpy.data.materials.get("Fur | warm integrated cream")

def create_cheek_hero_mass(name, pos, scale, rot_euler, mat):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=10, radius=1.0, location=pos)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    obj.rotation_euler = rot_euler

    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

    # Subdivide for smoothness
    mod = obj.modifiers.new("Sub", 'SUBSURF')
    mod.levels = 1
    mod.render_levels = 1
    bpy.ops.object.modifier_apply(modifier="Sub")

    # Add organic noise
    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.normal_update()
    for v in bm.verts:
        # Slight outward noise
        noise = (random.random() - 0.5) * 0.02
        if v.normal.length > 0.001:
            v.co += v.normal * noise
    bm.to_mesh(me)
    bm.free()
    me.update()

    for poly in obj.data.polygons:
        poly.use_smooth = True

    if mat:
        obj.data.materials.append(mat)

    obj_map[name] = obj
    return obj

hero_cheek_count = 0

# LEFT side hero cheek masses - large, overlapping, dramatic
for i, (x, y, z, sx, sy, sz, rx, ry, rz) in enumerate([
    # (x_offset, y_offset, z_offset, scale_x, scale_y, scale_z, rot_x, rot_y, rot_z)
    (0.58, -0.12, -0.02,  0.28, 0.18, 0.22,  10, 0, -20),   # Main lower mass
    (0.55, -0.06,  0.12,  0.24, 0.15, 0.20,  5, 0, -30),    # Upper mass
    (0.62, -0.15,  0.05,  0.20, 0.12, 0.18,  -5, 0, -15),   # Outer mass
    (0.50, -0.18, -0.08,  0.18, 0.14, 0.16,  15, 0, -10),   # Lower outer mass
    (0.48,  0.00,  0.15,  0.16, 0.10, 0.14,  -10, 0, -25),  # Upper inner transition
]):
    pos = (center.x + x, center.y + y, head_z + z)
    mass = create_cheek_hero_mass(
        f"KIKO | cheek hero L {i+1}",
        pos,
        (sx, sy, sz),
        (math.radians(rx), math.radians(ry), math.radians(rz)),
        cream_mat
    )
    hero_cheek_count += 1

# RIGHT side - mirror
for i, (x, y, z, sx, sy, sz, rx, ry, rz) in enumerate([
    (-0.58, -0.12, -0.02,  0.28, 0.18, 0.22,  10, 0, 20),
    (-0.55, -0.06,  0.12,  0.24, 0.15, 0.20,  5, 0, 30),
    (-0.62, -0.15,  0.05,  0.20, 0.12, 0.18,  -5, 0, 15),
    (-0.50, -0.18, -0.08,  0.18, 0.14, 0.16,  15, 0, 10),
    (-0.48,  0.00,  0.15,  0.16, 0.10, 0.14,  -10, 0, 25),
]):
    pos = (center.x + x, center.y + y, head_z + z)
    mass = create_cheek_hero_mass(
        f"KIKO | cheek hero R {i+1}",
        pos,
        (sx, sy, sz),
        (math.radians(rx), math.radians(ry), math.radians(rz)),
        cream_mat
    )
    hero_cheek_count += 1

print(f"  Added {hero_cheek_count} hero cheek masses")

# ================================================================
# ITERATION 2 FIX 2 — CREST EDGE SOFTENING
# ================================================================
print("\n=== ITER2: Crest edge softening ===")

for i in range(1, 11):
    name = f"KIKO | layered crest lock {i:02d}"
    obj = obj_map.get(name)
    if not obj:
        continue

    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.normal_update()

    local_verts = [v.co.copy() for v in bm.verts]
    if not local_verts:
        bm.free()
        continue

    min_z = min(v.z for v in local_verts)
    max_z = max(v.z for v in local_verts)
    z_range = max_z - min_z
    c_local = sum(local_verts, Vector((0,0,0))) / len(local_verts)

    random.seed(i * 11 + 5)

    # Add more organic edge irregularity
    for v in bm.verts:
        t = (v.co.z - min_z) / max(z_range, 0.001)
        dist_from_center = (v.co - c_local).length

        # Add edge waviness proportional to distance from center axis
        if dist_from_center > 0.02:
            wave = math.sin(t * math.pi * 3 + i * 1.2) * 0.012 * dist_from_center
            noise = (random.random() - 0.5) * 0.008
            if v.normal.length > 0.001:
                v.co += v.normal * (wave + noise)

        # Further soften tips
        if t > 0.75:
            tip_factor = (t - 0.75) / 0.25
            offset = v.co - c_local
            v.co.x = c_local.x + offset.x * (1 - tip_factor * 0.2)
            v.co.y = c_local.y + offset.y * (1 - tip_factor * 0.2)

    bm.to_mesh(me)
    bm.free()
    me.update()

print("  Softened all 10 crest locks")

# ================================================================
# ITERATION 2 FIX 3 — BODY SILHOUETTE ENHANCEMENT
# ================================================================
print("\n=== ITER2: Body silhouette enhancement ===")

# Add a few more strategic fur masses at key silhouette points
body_fur_extra = 0
fur_teal = bpy.data.materials.get("Fur | deep teal blue-gray")
fur_highlight = bpy.data.materials.get("Fur | soft teal highlights")

# Upper arms / shoulder caps
for side, sign in [("L", 1), ("R", -1)]:
    for j in range(2):
        y_off = -0.1 + j * 0.15
        pos = (center.x + sign * 0.50, center.y + y_off,
               all_min.z + height * 0.50 + j * 0.06)
        bpy.ops.mesh.primitive_uv_sphere_add(
            segments=10, ring_count=6, radius=1.0, location=pos)
        m = bpy.context.object
        m.name = f"KIKO | upper arm fur {side} {j+1}"
        m.scale = (0.08, 0.06, 0.10)
        bpy.context.view_layer.objects.active = m
        bpy.ops.object.transform_apply(scale=True)
        for poly in m.data.polygons:
            poly.use_smooth = True
        if fur_teal:
            m.data.materials.append(fur_teal)
        obj_map[m.name] = m
        body_fur_extra += 1

# Hips / lower back
for side, sign in [("L", 1), ("R", -1)]:
    pos = (center.x + sign * 0.28, center.y + 0.10,
           all_min.z + height * 0.30)
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=10, ring_count=6, radius=1.0, location=pos)
    m = bpy.context.object
    m.name = f"KIKO | hip tuft {side}"
    m.scale = (0.09, 0.07, 0.08)
    bpy.context.view_layer.objects.active = m
    bpy.ops.object.transform_apply(scale=True)
    for poly in m.data.polygons:
        poly.use_smooth = True
    if fur_teal:
        m.data.materials.append(fur_teal)
    obj_map[m.name] = m
    body_fur_extra += 1

# Wrist tufts
for side, sign in [("L", 1), ("R", -1)]:
    pos = (center.x + sign * 0.58, center.y - 0.04,
           all_min.z + height * 0.32)
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=8, ring_count=5, radius=1.0, location=pos)
    m = bpy.context.object
    m.name = f"KIKO | wrist tuft {side}"
    m.scale = (0.06, 0.05, 0.07)
    bpy.context.view_layer.objects.active = m
    bpy.ops.object.transform_apply(scale=True)
    for poly in m.data.polygons:
        poly.use_smooth = True
    if fur_highlight:
        m.data.materials.append(fur_highlight)
    obj_map[m.name] = m
    body_fur_extra += 1

print(f"  Added {body_fur_extra} extra body fur masses")

# ================================================================
# SAVE AND RE-EXPORT
# ================================================================
print("\n=== Saving and exporting iter2 ===")

bpy.ops.wm.save_as_mainfile(filepath=BLEND_V3)
print(f"  Saved: {BLEND_V3}")

bpy.ops.export_scene.gltf(
    filepath=GLB_V3,
    export_format='GLB',
    use_selection=False,
    export_apply=True,
    export_materials='EXPORT',
    export_normals=True,
)

fsize = os.path.getsize(GLB_V3)
print(f"  Exported: {GLB_V3} ({fsize/1024/1024:.1f} MB)")

# Final stats
final_objects = len([o for o in bpy.data.objects if o.type == 'MESH'])
final_verts = sum(len(o.data.vertices) for o in bpy.data.objects if o.type == 'MESH')
final_faces = sum(len(o.data.polygons) for o in bpy.data.objects if o.type == 'MESH')
print(f"  Final: {final_objects} meshes, {final_verts} verts, {final_faces} faces")

# ================================================================
# RE-RENDER ALL VIEWS
# ================================================================
print("\n=== Re-rendering all views ===")

# Remove old render infrastructure
for obj in list(bpy.data.objects):
    if obj.type in ('CAMERA', 'LIGHT', 'EMPTY') or obj.name == "GroundPlane":
        bpy.data.objects.remove(obj, do_unlink=True)

# Recompute bounds
all_min2 = Vector((float('inf'),) * 3)
all_max2 = Vector((float('-inf'),) * 3)
for obj in bpy.data.objects:
    if obj.type == 'MESH':
        for v in obj.data.vertices:
            co = obj.matrix_world @ v.co
            for i in range(3):
                if co[i] < all_min2[i]: all_min2[i] = co[i]
                if co[i] > all_max2[i]: all_max2[i] = co[i]

center2 = (all_min2 + all_max2) / 2
height2 = all_max2.z - all_min2.z
focus_z2 = all_min2.z + height2 * 0.50
face_z2 = all_min2.z + height2 * 0.82
crest_z2 = all_min2.z + height2 * 0.92

# Scene setup
scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 1080
scene.render.resolution_y = 1080
scene.render.resolution_percentage = 100
scene.render.film_transparent = False
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'
try:
    scene.eevee.taa_render_samples = 64
except:
    pass

# World
world = bpy.data.worlds.new("StudioWorld2")
scene.world = world
world.use_nodes = True
nodes = world.node_tree.nodes
links = world.node_tree.links
nodes.clear()
bg = nodes.new('ShaderNodeBackground')
bg.inputs['Color'].default_value = (0.25, 0.24, 0.23, 1.0)
bg.inputs['Strength'].default_value = 1.0
output = nodes.new('ShaderNodeOutputWorld')
links.new(bg.outputs['Background'], output.inputs['Surface'])

# Lighting
cam_dist2 = height2 * 2.5

def add_light2(name, location, energy, size=3.0, color=(1, 0.98, 0.95)):
    bpy.ops.object.light_add(type='AREA', location=location)
    l = bpy.context.object
    l.name = name
    l.data.energy = energy
    l.data.size = size
    l.data.color = color
    d = center2 - Vector(location)
    l.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()

add_light2("Key2", (center2.x + cam_dist2*0.7, center2.y - cam_dist2*0.8, focus_z2 + height2*0.8), 400, 4.0, (1,0.97,0.92))
add_light2("Fill2", (center2.x - cam_dist2*0.8, center2.y - cam_dist2*0.5, focus_z2 + height2*0.2), 150, 5.0, (0.88,0.92,1))
add_light2("Rim2", (center2.x, center2.y + cam_dist2*0.8, focus_z2 + height2*0.6), 300, 3.0, (1,0.92,0.82))
add_light2("Bounce2", (center2.x, center2.y - cam_dist2*0.3, all_min2.z - 0.3), 50, 6.0, (0.95,0.92,0.88))

# Ground
bpy.ops.mesh.primitive_plane_add(size=30, location=(center2.x, center2.y, all_min2.z - 0.005))
ground = bpy.context.object
ground.name = "GroundPlane"
gm = bpy.data.materials.new("GroundMat2")
gm.use_nodes = True
gm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.30, 0.29, 0.28, 1)
gm.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.85
ground.data.materials.append(gm)

# Camera
bpy.ops.object.camera_add()
cam = bpy.context.object
cam.name = "RenderCam2"
scene.camera = cam

bpy.ops.object.empty_add(type='PLAIN_AXES', location=(center2.x, center2.y, focus_z2))
tgt = bpy.context.object
tgt.name = "CamTarget2"

def aim(angle_deg, elev_deg, dist, tz, lens=85):
    a = math.radians(angle_deg)
    e = math.radians(elev_deg)
    cam.location = (
        center2.x + dist * math.sin(a) * math.cos(e),
        center2.y - dist * math.cos(a) * math.cos(e),
        tz + dist * math.sin(e)
    )
    cam.data.lens = lens
    tgt.location = (center2.x, center2.y, tz)
    for c in cam.constraints:
        cam.constraints.remove(c)
    ct = cam.constraints.new(type='TRACK_TO')
    ct.target = tgt
    ct.track_axis = 'TRACK_NEGATIVE_Z'
    ct.up_axis = 'UP_Y'

# Standard views
views = [
    ("01_front",         0,   8,  cam_dist2,       focus_z2,  85),
    ("02_three_quarter", 40,  10, cam_dist2,       focus_z2,  85),
    ("03_side",          90,  8,  cam_dist2,       focus_z2,  85),
    ("04_back",          180, 10, cam_dist2,       focus_z2,  85),
    ("05_face_closeup",  8,   3,  height2 * 0.75,  face_z2,   100),
    ("06_eye_closeup",   3,   0,  height2 * 0.4,   face_z2 - 0.05, 120),
    ("07_crest_detail",  15,  30, height2 * 0.6,   crest_z2,  100),
    ("08_tail_profile",  120, 5,  cam_dist2 * 0.8, focus_z2 - 0.3, 85),
]

rendered = {}
for name, angle, elev, dist, tz, lens in views:
    print(f"  Rendering {name}...")
    aim(angle, elev, dist, tz, lens)
    bpy.context.view_layer.update()
    fp = os.path.join(OUT_DIR, f"{name}.png")
    scene.render.filepath = fp
    bpy.ops.render.render(write_still=True)
    rendered[name] = fp

# Silhouettes
print("  Rendering silhouettes...")
orig_mats = {}
for obj in bpy.data.objects:
    if obj.type == 'MESH' and obj.name != "GroundPlane":
        orig_mats[obj.name] = list(obj.data.materials)

sil_mat = bpy.data.materials.new("SilMat2")
sil_mat.use_nodes = True
sil_mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.02, 0.02, 0.02, 1)
sil_mat.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 1.0

for obj in bpy.data.objects:
    if obj.type == 'MESH' and obj.name != "GroundPlane":
        obj.data.materials.clear()
        obj.data.materials.append(sil_mat)
bg.inputs['Color'].default_value = (0.95, 0.95, 0.95, 1)
bg.inputs['Strength'].default_value = 1.5
ground.hide_render = True

for name, angle, elev, dist, tz, lens in [
    ("09_black_silhouette_front", 0, 8, cam_dist2, focus_z2, 85),
    ("10_black_silhouette_three_quarter", 40, 10, cam_dist2, focus_z2, 85),
]:
    print(f"  Rendering {name}...")
    aim(angle, elev, dist, tz, lens)
    bpy.context.view_layer.update()
    fp = os.path.join(OUT_DIR, f"{name}.png")
    scene.render.filepath = fp
    bpy.ops.render.render(write_still=True)
    rendered[name] = fp

# Restore
for obj in bpy.data.objects:
    if obj.type == 'MESH' and obj.name in orig_mats:
        obj.data.materials.clear()
        for mat in orig_mats[obj.name]:
            obj.data.materials.append(mat)
bg.inputs['Color'].default_value = (0.25, 0.24, 0.23, 1)
bg.inputs['Strength'].default_value = 1.0
ground.hide_render = False

# V2 vs V3 comparison
print("  Creating comparisons...")
V2_DIR = os.path.join(PROJECT, "review/kiko_visual")

def load_img(path):
    img = bpy.data.images.load(path)
    w, h = img.size
    px = list(img.pixels[:])
    bpy.data.images.remove(img)
    return w, h, px

def save_img(path, w, h, px):
    img = bpy.data.images.new("comp", width=w, height=h, alpha=True)
    img.pixels = px
    img.filepath_raw = path
    img.file_format = 'PNG'
    img.save_render(path)
    bpy.data.images.remove(img)

def side_by_side(left, right, out, tw=1080, th=1080):
    hw = tw // 2
    lw, lh, lp = load_img(left)
    rw, rh, rp = load_img(right)
    px = [0.15, 0.15, 0.15, 1.0] * (tw * th)
    for y in range(min(th, lh)):
        for x in range(min(hw, lw)):
            si = (y * lw + x) * 4
            di = (y * tw + x) * 4
            if si+3 < len(lp): px[di:di+4] = lp[si:si+4]
    for y in range(min(th, rh)):
        for x in range(min(hw, rw)):
            si = (y * rw + x) * 4
            di = (y * tw + (hw + x)) * 4
            if si+3 < len(rp): px[di:di+4] = rp[si:si+4]
    for y in range(th):
        for dx in range(-1, 2):
            x = hw + dx
            if 0 <= x < tw:
                di = (y * tw + x) * 4
                px[di:di+4] = [0.8, 0.8, 0.8, 1.0]
    save_img(out, tw, th, px)

v2_front = os.path.join(V2_DIR, "front.png")
v3_front = os.path.join(OUT_DIR, "01_front.png")
if os.path.exists(v2_front) and os.path.exists(v3_front):
    cp = os.path.join(OUT_DIR, "11_v2_vs_v3_face.png")
    side_by_side(v2_front, v3_front, cp)
    rendered["11_v2_vs_v3_face"] = cp
    print(f"  Created: 11_v2_vs_v3_face.png")

v3_sil = os.path.join(OUT_DIR, "09_black_silhouette_front.png")
if os.path.exists(v2_front) and os.path.exists(v3_sil):
    cp = os.path.join(OUT_DIR, "12_v2_vs_v3_silhouette.png")
    side_by_side(v2_front, v3_sil, cp)
    rendered["12_v2_vs_v3_silhouette"] = cp
    print(f"  Created: 12_v2_vs_v3_silhouette.png")

print(f"\n=== ITERATION 2 COMPLETE ===")
print(f"Total renders: {len(rendered)}")
