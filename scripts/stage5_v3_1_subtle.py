"""
Stage 5.2 — V3.1 Subtle Refinement
Starts fresh from V2. Makes ONLY 4 localized changes:
  1. Cheeks: +10-15% width with 2-3 broad soft masses per side
  2. Muzzle: slightly reduce oval, blend into cheeks
  3. Crest: soften curvature, reduce blade/horn appearance
  4. Tail: improve outer silhouette with broad overlapping plume forms

NO noise displacement, NO aggressive scaling, NO body-wide fur clumps.
"""
import bpy
import bmesh
import os
import math
from mathutils import Vector

PROJECT = "/Users/macbook/Automation-Workplace/cartoon-maker"
GLB_V2 = os.path.join(PROJECT, "assets/characters/kiko_final/source/KIKO_source_v2.glb")
GLB_V3_1 = os.path.join(PROJECT, "assets/characters/kiko_final/source/KIKO_source_v3_1.glb")
BLEND_V3_1 = os.path.join(PROJECT, "projects/characters/kiko/blends/master/KIKO_visual_stage5_v3_1.blend")
REVIEW_DIR = os.path.join(PROJECT, "projects/characters/kiko/review/stage5_v3_1")
os.makedirs(REVIEW_DIR, exist_ok=True)
os.makedirs(os.path.dirname(BLEND_V3_1), exist_ok=True)

# ================================================================
# Import V2 clean
# ================================================================
print("=== Importing V2 (clean) ===")
bpy.ops.wm.read_homefile(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB_V2)

obj_map = {obj.name: obj for obj in bpy.data.objects}
print(f"  {len(obj_map)} objects")

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
print(f"  Height: {height:.3f}")


# ================================================================
# FIX MATERIALS FIRST (same proven color map)
# ================================================================
print("\n=== Fixing materials ===")

MATERIAL_COLORS = {
    "Fur | deep teal blue-gray":    ((0.18, 0.28, 0.30, 1), 0.85, 0.0, 0.3),
    "Fur | soft teal highlights":   ((0.30, 0.45, 0.48, 1), 0.80, 0.0, 0.3),
    "Fur | warm integrated cream":  ((0.85, 0.78, 0.65, 1), 0.82, 0.0, 0.3),
    "Fur | pale muzzle":            ((0.90, 0.84, 0.75, 1), 0.80, 0.0, 0.3),
    "Fur | burnt apricot":          ((0.75, 0.40, 0.18, 1), 0.82, 0.0, 0.3),
    "Fur | deep shadow":            ((0.10, 0.15, 0.17, 1), 0.90, 0.0, 0.3),
    "Eye | amber iris":             ((0.85, 0.55, 0.12, 1), 0.15, 0.0, 0.5),
    "Eye | honey iris center":      ((0.95, 0.72, 0.20, 1), 0.10, 0.0, 0.5),
    "Eye | deep warm pupil":        ((0.02, 0.01, 0.01, 1), 0.05, 0.0, 0.5),
    "Eye | soft catchlight":        ((1.0, 1.0, 1.0, 1),    0.00, 0.0, 0.5),
    "Eye | warm ivory":             ((0.95, 0.93, 0.88, 1), 0.25, 0.0, 0.45),
    "Ear | warm coral velvet":      ((0.82, 0.45, 0.35, 1), 0.88, 0.0, 0.3),
    "Nose | rosewood":              ((0.30, 0.15, 0.13, 1), 0.40, 0.0, 0.45),
    "Mouth | warm dark umber":      ((0.20, 0.10, 0.08, 1), 0.70, 0.0, 0.3),
    "Cloth | worn jungle teal":     ((0.22, 0.32, 0.30, 1), 0.82, 0.0, 0.3),
    "Cloth | faded olive panels":   ((0.35, 0.38, 0.25, 1), 0.85, 0.0, 0.3),
    "Cloth | persimmon scarf":      ((0.80, 0.30, 0.12, 1), 0.75, 0.0, 0.35),
    "Cloth | scarf highlights":     ((0.88, 0.42, 0.18, 1), 0.72, 0.0, 0.35),
    "Leather | dark walnut":        ((0.22, 0.13, 0.08, 1), 0.60, 0.0, 0.40),
    "Leather | worn saddle":        ((0.42, 0.28, 0.15, 1), 0.55, 0.0, 0.40),
    "Hardware | aged brass":        ((0.72, 0.58, 0.22, 1), 0.35, 0.85, 0.5),
    "Thread | flax":                ((0.70, 0.62, 0.45, 1), 0.88, 0.0, 0.3),
}

for mat in bpy.data.materials:
    if mat.name in MATERIAL_COLORS and mat.use_nodes:
        base, rough, metal, spec = MATERIAL_COLORS[mat.name]
        for node in mat.node_tree.nodes:
            if node.type == 'BSDF_PRINCIPLED':
                node.inputs['Base Color'].default_value = base
                node.inputs['Roughness'].default_value = rough
                node.inputs['Metallic'].default_value = metal
                try:
                    node.inputs['Specular IOR Level'].default_value = spec
                except:
                    try:
                        node.inputs['Specular'].default_value = spec
                    except:
                        pass
        # Catchlight emission
        if mat.name == "Eye | soft catchlight":
            for node in mat.node_tree.nodes:
                if node.type == 'BSDF_PRINCIPLED':
                    try:
                        node.inputs['Emission Color'].default_value = (1, 1, 1, 1)
                        node.inputs['Emission Strength'].default_value = 0.5
                    except:
                        pass

print("  22 materials fixed")


# ================================================================
# CHANGE 1: CHEEKS — subtle 10-15% width, 2-3 broad soft masses
# ================================================================
print("\n=== Change 1: Subtle cheek expansion ===")

# A) Gently scale existing cheek tufts — only 15% larger
for name in ["KIKO | cheek tuft L 1", "KIKO | cheek tuft L 2", "KIKO | cheek tuft L 3",
             "KIKO | cheek tuft R 1", "KIKO | cheek tuft R 2", "KIKO | cheek tuft R 3"]:
    obj = obj_map.get(name)
    if obj:
        me = obj.data
        bm = bmesh.new()
        bm.from_mesh(me)
        c = sum((v.co.copy() for v in bm.verts), Vector()) / len(bm.verts)
        for v in bm.verts:
            offset = v.co - c
            v.co = c + Vector((offset.x * 1.15, offset.y * 1.10, offset.z * 1.15))
        bm.to_mesh(me)
        bm.free()
        me.update()

# B) Gently expand cheek/muzzle mesh laterally — modest push
cheek_muzzle = obj_map.get("KIKO | integrated cream cheeks and muzzle")
if cheek_muzzle:
    me = cheek_muzzle.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.normal_update()
    for v in bm.verts:
        world_co = cheek_muzzle.matrix_world @ v.co
        z_rel = (world_co.z - (head_z - 0.5)) / 1.0
        if 0.1 < z_rel < 0.8:
            x_offset = world_co.x - center.x
            if abs(x_offset) > 0.15:
                # Gentle 8% lateral push
                lateral = min(abs(x_offset) / 0.5, 1.0) * 0.05
                sign = 1 if x_offset > 0 else -1
                local_dir = cheek_muzzle.matrix_world.inverted().to_3x3() @ Vector((sign, 0, 0))
                v.co += local_dir * lateral
    bm.to_mesh(me)
    bm.free()
    me.update()

# C) Add 2 broad soft cheek masses per side — smooth, no noise
cream_mat = bpy.data.materials.get("Fur | warm integrated cream")

def create_smooth_cheek_mass(name, position, scale, rotation_deg):
    """Create a single smooth, broad cheek mass. No noise."""
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=16, ring_count=10, radius=1.0, location=position)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    obj.rotation_euler = (
        math.radians(rotation_deg[0]),
        math.radians(rotation_deg[1]),
        math.radians(rotation_deg[2])
    )
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

    # One level of subdivision for smoothness
    mod = obj.modifiers.new("Sub", 'SUBSURF')
    mod.levels = 1
    mod.render_levels = 1
    bpy.ops.object.modifier_apply(modifier="Sub")

    # Smooth shade
    for poly in obj.data.polygons:
        poly.use_smooth = True

    if cream_mat:
        obj.data.materials.append(cream_mat)

    obj_map[name] = obj
    return obj

# Left cheek: 2 masses — one lower-outer, one upper-mid
# These flow outward/backward from muzzle
create_smooth_cheek_mass(
    "KIKO | cheek mass L lower",
    (center.x + 0.48, center.y - 0.10, head_z - 0.04),
    (0.16, 0.10, 0.14),
    (5, 0, -15)  # slight tilt flowing backward
)
create_smooth_cheek_mass(
    "KIKO | cheek mass L upper",
    (center.x + 0.44, center.y - 0.06, head_z + 0.10),
    (0.14, 0.09, 0.12),
    (0, 0, -20)
)

# Right cheek: mirror
create_smooth_cheek_mass(
    "KIKO | cheek mass R lower",
    (center.x - 0.48, center.y - 0.10, head_z - 0.04),
    (0.16, 0.10, 0.14),
    (5, 0, 15)
)
create_smooth_cheek_mass(
    "KIKO | cheek mass R upper",
    (center.x - 0.44, center.y - 0.06, head_z + 0.10),
    (0.14, 0.09, 0.12),
    (0, 0, 20)
)

print("  6 existing tufts scaled 15%, muzzle expanded 8%, 4 cheek masses added")


# ================================================================
# CHANGE 2: MUZZLE — slightly reduce oval, blend into cheeks
# ================================================================
print("\n=== Change 2: Muzzle refinement ===")

if cheek_muzzle:
    me = cheek_muzzle.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.normal_update()

    # Find muzzle center region (front, lower-mid face)
    for v in bm.verts:
        world_co = cheek_muzzle.matrix_world @ v.co
        z_rel = (world_co.z - (head_z - 0.5)) / 1.0

        # Target the central muzzle oval only (not cheeks)
        x_from_center = abs(world_co.x - center.x)
        y_from_center = world_co.y - center.y  # negative = front

        if x_from_center < 0.25 and y_from_center < -0.08 and 0.2 < z_rel < 0.6:
            # Gently pull inward/back by ~5%
            inward = v.normal * (-0.015)
            v.co += inward

    bm.to_mesh(me)
    bm.free()
    me.update()

print("  Muzzle oval reduced ~5% at center")


# ================================================================
# CHANGE 3: CREST — soften curvature, reduce blade appearance
# ================================================================
print("\n=== Change 3: Crest softening ===")

for i in range(1, 11):
    name = f"KIKO | layered crest lock {i:02d}"
    obj = obj_map.get(name)
    if not obj:
        continue

    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.normal_update()

    verts = [v.co.copy() for v in bm.verts]
    if not verts:
        bm.free()
        continue

    min_z = min(v.z for v in verts)
    max_z = max(v.z for v in verts)
    z_range = max_z - min_z
    c_local = sum(verts, Vector()) / len(verts)

    for v in bm.verts:
        t = (v.co.z - min_z) / max(z_range, 0.001)  # 0=base, 1=tip
        offset = v.co - c_local

        # Widen roots by 10% to reduce blade look
        if t < 0.3:
            root_factor = (0.3 - t) / 0.3 * 0.10
            v.co.x += offset.x * root_factor
            v.co.y += offset.y * root_factor

        # Soften tips — make rounder, less pointy
        if t > 0.7:
            tip_factor = (t - 0.7) / 0.3
            taper = 1.0 - tip_factor * 0.2  # gentler taper than iter2
            v.co.x = c_local.x + offset.x * taper
            v.co.y = c_local.y + offset.y * taper

        # Very subtle curve (not twist) — slight lean
        lean = 0.02 * t * t * math.sin(i * 0.8)
        v.co.x += lean

    bm.to_mesh(me)
    bm.free()
    me.update()

print("  10 crest locks softened (wider roots, rounder tips, subtle lean)")


# ================================================================
# CHANGE 4: TAIL — broad overlapping plume forms at outer silhouette
# ================================================================
print("\n=== Change 4: Tail silhouette improvement ===")

tail_main = obj_map.get("KIKO | dominant curved plume tail")

# Get tail center and direction
if tail_main:
    tail_verts = [tail_main.matrix_world @ v.co for v in tail_main.data.vertices]
    tail_center = sum(tail_verts, Vector()) / len(tail_verts)
    tail_min_z = min(v.z for v in tail_verts)
    tail_max_z = max(v.z for v in tail_verts)
else:
    tail_center = center.copy()
    tail_center.x -= 0.8
    tail_min_z = all_min.z + height * 0.1
    tail_max_z = all_min.z + height * 0.5

# Add 5 broad overlapping plume forms around the tail outer edge
# These are smooth, elongated shapes — NOT spikes
mat_choices = {
    0: "Fur | deep teal blue-gray",
    1: "Fur | warm integrated cream",
    2: "Fur | burnt apricot",
    3: "Fur | deep teal blue-gray",
    4: "Fur | soft teal highlights",
}

plume_count = 0
for i in range(5):
    # Position around the tail's outer perimeter
    angle = math.radians(-60 + i * 30)  # spread around outer edge
    z_pos = tail_center.z + (i - 2) * 0.12  # stagger vertically
    r = 0.22  # offset from tail center

    pos = (
        tail_center.x + r * math.cos(angle) * 0.5,  # mostly lateral
        tail_center.y + r * math.sin(angle),
        z_pos
    )

    # Elongated smooth shape flowing along tail direction
    mat_name = mat_choices.get(i, "Fur | deep teal blue-gray")
    mat = bpy.data.materials.get(mat_name)

    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=12, ring_count=8, radius=1.0, location=pos)
    plume = bpy.context.object
    plume.name = f"KIKO | tail plume form {i+1:02d}"

    # Elongated: long in Z (along tail), moderate width
    length = 0.18 + i * 0.02  # varied lengths
    plume.scale = (0.06, 0.05, length)

    # Rotate to follow tail curve
    plume.rotation_euler = (
        math.radians(20 + i * 5),   # tilt along tail
        math.radians(angle * 0.3),  # follow curve
        math.radians(-30 + i * 10)  # fan out
    )

    bpy.context.view_layer.objects.active = plume
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

    # Smooth subdivision
    mod = plume.modifiers.new("Sub", 'SUBSURF')
    mod.levels = 1
    mod.render_levels = 1
    bpy.ops.object.modifier_apply(modifier="Sub")

    for poly in plume.data.polygons:
        poly.use_smooth = True

    if mat:
        plume.data.materials.append(mat)

    obj_map[plume.name] = plume
    plume_count += 1

print(f"  Added {plume_count} broad tail plume forms")


# ================================================================
# SAVE AND EXPORT
# ================================================================
print("\n=== Saving V3.1 ===")
bpy.ops.wm.save_as_mainfile(filepath=BLEND_V3_1)

bpy.ops.export_scene.gltf(
    filepath=GLB_V3_1,
    export_format='GLB',
    use_selection=False,
    export_apply=True,
    export_materials='EXPORT',
    export_normals=True,
)

fsize = os.path.getsize(GLB_V3_1)
final_objs = len([o for o in bpy.data.objects if o.type == 'MESH'])
final_verts = sum(len(o.data.vertices) for o in bpy.data.objects if o.type == 'MESH')
print(f"  Blend: {BLEND_V3_1}")
print(f"  GLB: {GLB_V3_1} ({fsize/1024/1024:.1f} MB)")
print(f"  Objects: {final_objs}, Verts: {final_verts}")


# ================================================================
# RENDER REVIEW SET
# ================================================================
print("\n=== Rendering review set ===")

# Clean render objects
for obj in list(bpy.data.objects):
    if obj.type in ('CAMERA', 'LIGHT', 'EMPTY'):
        bpy.data.objects.remove(obj, do_unlink=True)

# Recompute bounds (slightly changed from cheek expansion)
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
focus_z = all_min2.z + height2 * 0.50
face_z = all_min2.z + height2 * 0.82
cam_dist = height2 * 2.5

# Scene
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
world = bpy.data.worlds.new("Studio")
scene.world = world
world.use_nodes = True
wnodes = world.node_tree.nodes
wlinks = world.node_tree.links
wnodes.clear()
wbg = wnodes.new('ShaderNodeBackground')
wbg.inputs['Color'].default_value = (0.25, 0.24, 0.23, 1.0)
wbg.inputs['Strength'].default_value = 1.0
wout = wnodes.new('ShaderNodeOutputWorld')
wlinks.new(wbg.outputs['Background'], wout.inputs['Surface'])

# Lights (same as V2 validation)
def add_light(name, loc, energy, size=3.0, color=(1, 0.98, 0.95)):
    bpy.ops.object.light_add(type='AREA', location=loc)
    l = bpy.context.object
    l.name = name
    l.data.energy = energy
    l.data.size = size
    l.data.color = color
    d = center2 - Vector(loc)
    l.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()

add_light("Key", (center2.x+cam_dist*0.7, center2.y-cam_dist*0.8, focus_z+height2*0.8), 400, 4, (1,0.97,0.92))
add_light("Fill", (center2.x-cam_dist*0.8, center2.y-cam_dist*0.5, focus_z+height2*0.2), 150, 5, (0.88,0.92,1))
add_light("Rim", (center2.x, center2.y+cam_dist*0.8, focus_z+height2*0.6), 300, 3, (1,0.92,0.82))
add_light("Bounce", (center2.x, center2.y-cam_dist*0.3, all_min2.z-0.3), 50, 6, (0.95,0.92,0.88))

# Ground
bpy.ops.mesh.primitive_plane_add(size=30, location=(center2.x, center2.y, all_min2.z-0.005))
gnd = bpy.context.object
gnd.name = "Ground"
gmat = bpy.data.materials.new("GroundMat")
gmat.use_nodes = True
gmat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.30, 0.29, 0.28, 1)
gmat.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.85
gnd.data.materials.append(gmat)

# Camera
bpy.ops.object.camera_add()
cam = bpy.context.object
cam.name = "Cam"
scene.camera = cam

bpy.ops.object.empty_add(type='PLAIN_AXES', location=(center2.x, center2.y, focus_z))
tgt = bpy.context.object
tgt.name = "CamTgt"

def aim(angle_deg, elev_deg, dist, tz, lens=85):
    a = math.radians(angle_deg)
    e = math.radians(elev_deg)
    cam.location = (center2.x + dist*math.sin(a)*math.cos(e),
                    center2.y - dist*math.cos(a)*math.cos(e),
                    tz + dist*math.sin(e))
    cam.data.lens = lens
    tgt.location = (center2.x, center2.y, tz)
    for c in cam.constraints:
        cam.constraints.remove(c)
    ct = cam.constraints.new(type='TRACK_TO')
    ct.target = tgt
    ct.track_axis = 'TRACK_NEGATIVE_Z'
    ct.up_axis = 'UP_Y'

# Render standard views
views = [
    ("front",          0,   8,  cam_dist,       focus_z,  85),
    ("three_quarter",  40,  10, cam_dist,       focus_z,  85),
    ("side",           90,  8,  cam_dist,       focus_z,  85),
    ("face_closeup",   8,   3,  height2*0.75,   face_z,   100),
    ("tail_profile",   120, 5,  cam_dist*0.8,   focus_z-0.3, 85),
]

rendered = {}
for name, angle, elev, dist, tz, lens in views:
    aim(angle, elev, dist, tz, lens)
    bpy.context.view_layer.update()
    fp = os.path.join(REVIEW_DIR, f"{name}.png")
    scene.render.filepath = fp
    bpy.ops.render.render(write_still=True)
    rendered[name] = fp
    print(f"  {name}: {os.path.getsize(fp)} bytes")

# Black silhouette
print("  Rendering silhouette...")
orig_mats = {}
for obj in bpy.data.objects:
    if obj.type == 'MESH' and obj.name != "Ground":
        orig_mats[obj.name] = list(obj.data.materials)

smat = bpy.data.materials.new("SilMat")
smat.use_nodes = True
smat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.02,0.02,0.02,1)
smat.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 1.0

for obj in bpy.data.objects:
    if obj.type == 'MESH' and obj.name != "Ground":
        obj.data.materials.clear()
        obj.data.materials.append(smat)
wbg.inputs['Color'].default_value = (0.95, 0.95, 0.95, 1)
wbg.inputs['Strength'].default_value = 1.5
gnd.hide_render = True

aim(0, 8, cam_dist, focus_z, 85)
bpy.context.view_layer.update()
fp = os.path.join(REVIEW_DIR, "silhouette_front.png")
scene.render.filepath = fp
bpy.ops.render.render(write_still=True)
rendered["silhouette_front"] = fp
print(f"  silhouette_front: {os.path.getsize(fp)} bytes")

# Restore materials
for obj in bpy.data.objects:
    if obj.type == 'MESH' and obj.name in orig_mats:
        obj.data.materials.clear()
        for m in orig_mats[obj.name]:
            obj.data.materials.append(m)
wbg.inputs['Color'].default_value = (0.25, 0.24, 0.23, 1)
wbg.inputs['Strength'].default_value = 1.0
gnd.hide_render = False

# V2-style front for comparison (render V3.1 at half width for side-by-side)
print("  Creating V3 vs V3.1 comparison...")
V2_REVIEW = os.path.join(PROJECT, "review/kiko_visual")
v2_front_path = os.path.join(V2_REVIEW, "front.png")

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

if os.path.exists(v2_front_path) and "front" in rendered:
    tw, th = 1080, 1080
    hw = tw // 2
    lw, lh, lp = load_img(v2_front_path)  # V2 colored (from previous V2 render)
    rw, rh, rp = load_img(rendered["front"])  # V3.1
    px = [0.15]*4 * (tw * th)
    for y in range(min(th, lh)):
        for x in range(min(hw, lw)):
            si = (y*lw+x)*4
            di = (y*tw+x)*4
            if si+3 < len(lp): px[di:di+4] = lp[si:si+4]
    for y in range(min(th, rh)):
        for x in range(min(hw, rw)):
            si = (y*rw+x)*4
            di = (y*tw+(hw+x))*4
            if si+3 < len(rp): px[di:di+4] = rp[si:si+4]
    for y in range(th):
        for dx in (-1, 0, 1):
            xx = hw + dx
            if 0 <= xx < tw:
                di = (y*tw+xx)*4
                px[di:di+4] = [0.8, 0.8, 0.8, 1.0]
    comp_path = os.path.join(REVIEW_DIR, "v2_vs_v3_1_front.png")
    save_img(comp_path, tw, th, px)
    rendered["comparison"] = comp_path
    print(f"  comparison: {os.path.getsize(comp_path)} bytes")

print(f"\n=== V3.1 COMPLETE ===")
print(f"Renders: {len(rendered)}")
