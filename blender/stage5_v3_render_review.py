"""
Stage 5.1 — V3 Review Render Set
Renders 12 comparison views from the V3 blend file using neutral studio lighting.
"""
import bpy
import os
import math
import json
from mathutils import Vector

PROJECT = "/Users/macbook/Automation-Workplace/cartoon-maker"
BLEND_V3 = os.path.join(PROJECT, "projects/characters/kiko/blends/master/KIKO_visual_stage5_v3.blend")
OUT_DIR = os.path.join(PROJECT, "projects/characters/kiko/review/stage5_v3")
V2_DIR = os.path.join(PROJECT, "review/kiko_visual")  # V2 renders for comparison
os.makedirs(OUT_DIR, exist_ok=True)

# ================================================================
# Load V3 blend
# ================================================================
bpy.ops.wm.open_mainfile(filepath=BLEND_V3)

# Remove any existing cameras/lights that might interfere
for obj in list(bpy.data.objects):
    if obj.type in ('CAMERA', 'LIGHT', 'EMPTY'):
        bpy.data.objects.remove(obj, do_unlink=True)

# ================================================================
# Compute character bounds
# ================================================================
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
focus_z = all_min.z + height * 0.50
face_z = all_min.z + height * 0.82
crest_z = all_min.z + height * 0.92

print(f"Bounds: height={height:.3f}, center={center}")

# ================================================================
# Scene setup — matching V2 render conditions
# ================================================================
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
world = bpy.data.worlds.new("StudioWorld")
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

# ================================================================
# Lighting — same as V2 validation
# ================================================================
cam_dist = height * 2.5

def add_light(name, location, energy, size=3.0, color=(1, 0.98, 0.95)):
    bpy.ops.object.light_add(type='AREA', location=location)
    light = bpy.context.object
    light.name = name
    light.data.energy = energy
    light.data.size = size
    light.data.color = color
    direction = center - Vector(location)
    light.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()

add_light("Key",
          (center.x + cam_dist * 0.7, center.y - cam_dist * 0.8, focus_z + height * 0.8),
          energy=400, size=4.0, color=(1.0, 0.97, 0.92))
add_light("Fill",
          (center.x - cam_dist * 0.8, center.y - cam_dist * 0.5, focus_z + height * 0.2),
          energy=150, size=5.0, color=(0.88, 0.92, 1.0))
add_light("Rim",
          (center.x, center.y + cam_dist * 0.8, focus_z + height * 0.6),
          energy=300, size=3.0, color=(1.0, 0.92, 0.82))
add_light("Bounce",
          (center.x, center.y - cam_dist * 0.3, all_min.z - 0.3),
          energy=50, size=6.0, color=(0.95, 0.92, 0.88))

# Ground plane
bpy.ops.mesh.primitive_plane_add(size=30, location=(center.x, center.y, all_min.z - 0.005))
ground = bpy.context.object
ground.name = "GroundPlane"
mat_ground = bpy.data.materials.new("GroundMat")
mat_ground.use_nodes = True
bsdf = mat_ground.node_tree.nodes["Principled BSDF"]
bsdf.inputs["Base Color"].default_value = (0.30, 0.29, 0.28, 1.0)
bsdf.inputs["Roughness"].default_value = 0.85
ground.data.materials.append(mat_ground)

# ================================================================
# Camera
# ================================================================
bpy.ops.object.camera_add()
cam_obj = bpy.context.object
cam_obj.name = "RenderCam"
scene.camera = cam_obj

bpy.ops.object.empty_add(type='PLAIN_AXES', location=(center.x, center.y, focus_z))
cam_target = bpy.context.object
cam_target.name = "CamTarget"

def aim_camera(angle_deg, elevation_deg, distance, target_z, lens=85):
    angle = math.radians(angle_deg)
    elev = math.radians(elevation_deg)
    cx = center.x + distance * math.sin(angle) * math.cos(elev)
    cy = center.y - distance * math.cos(angle) * math.cos(elev)
    cz = target_z + distance * math.sin(elev)
    cam_obj.location = (cx, cy, cz)
    cam_obj.data.lens = lens
    cam_target.location = (center.x, center.y, target_z)
    for c in cam_obj.constraints:
        cam_obj.constraints.remove(c)
    constraint = cam_obj.constraints.new(type='TRACK_TO')
    constraint.target = cam_target
    constraint.track_axis = 'TRACK_NEGATIVE_Z'
    constraint.up_axis = 'UP_Y'

# ================================================================
# Render views 01-08 (standard + detail)
# ================================================================
views = [
    ("01_front",           0,   8,  cam_dist,        focus_z,  85),
    ("02_three_quarter",   40,  10, cam_dist,        focus_z,  85),
    ("03_side",            90,  8,  cam_dist,        focus_z,  85),
    ("04_back",            180, 10, cam_dist,        focus_z,  85),
    ("05_face_closeup",    8,   3,  height * 0.75,   face_z,   100),
    ("06_eye_closeup",     3,   0,  height * 0.4,    face_z - 0.05, 120),
    ("07_crest_detail",    15,  30, height * 0.6,    crest_z,  100),
    ("08_tail_profile",    120, 5,  cam_dist * 0.8,  focus_z - 0.3, 85),
]

rendered = {}
for name, angle, elev, dist, tz, lens in views:
    print(f"Rendering {name}...")
    aim_camera(angle, elev, dist, tz, lens)
    bpy.context.view_layer.update()
    filepath = os.path.join(OUT_DIR, f"{name}.png")
    scene.render.filepath = filepath
    bpy.ops.render.render(write_still=True)
    rendered[name] = filepath
    fsize = os.path.getsize(filepath)
    print(f"  -> {fsize} bytes")

# ================================================================
# View 09-10: Black silhouette renders
# ================================================================
print("\nRendering silhouettes...")

# Store original materials
original_mats = {}
for obj in bpy.data.objects:
    if obj.type == 'MESH' and obj.name != "GroundPlane":
        original_mats[obj.name] = list(obj.data.materials)

# Create black silhouette material
sil_mat = bpy.data.materials.new("SilhouetteMat")
sil_mat.use_nodes = True
sil_bsdf = sil_mat.node_tree.nodes["Principled BSDF"]
sil_bsdf.inputs["Base Color"].default_value = (0.02, 0.02, 0.02, 1.0)
sil_bsdf.inputs["Roughness"].default_value = 1.0
sil_bsdf.inputs["Metallic"].default_value = 0.0

# Override white background
bg.inputs['Color'].default_value = (0.95, 0.95, 0.95, 1.0)
bg.inputs['Strength'].default_value = 1.5

# Hide ground for silhouette
ground.hide_render = True

# Apply silhouette material
for obj in bpy.data.objects:
    if obj.type == 'MESH' and obj.name != "GroundPlane":
        obj.data.materials.clear()
        obj.data.materials.append(sil_mat)

sil_views = [
    ("09_black_silhouette_front",          0,  8,  cam_dist, focus_z, 85),
    ("10_black_silhouette_three_quarter",   40, 10, cam_dist, focus_z, 85),
]

for name, angle, elev, dist, tz, lens in sil_views:
    print(f"Rendering {name}...")
    aim_camera(angle, elev, dist, tz, lens)
    bpy.context.view_layer.update()
    filepath = os.path.join(OUT_DIR, f"{name}.png")
    scene.render.filepath = filepath
    bpy.ops.render.render(write_still=True)
    rendered[name] = filepath
    fsize = os.path.getsize(filepath)
    print(f"  -> {fsize} bytes")

# Restore original materials
for obj in bpy.data.objects:
    if obj.type == 'MESH' and obj.name in original_mats:
        obj.data.materials.clear()
        for mat in original_mats[obj.name]:
            obj.data.materials.append(mat)

# Restore world
bg.inputs['Color'].default_value = (0.25, 0.24, 0.23, 1.0)
bg.inputs['Strength'].default_value = 1.0
ground.hide_render = False

# ================================================================
# Views 11-12: V2 vs V3 comparison (side by side via compositor)
# ================================================================
print("\nCreating V2 vs V3 comparisons...")

# For comparison renders, we'll render V3 at half width and stitch with V2
# Render V3 face at 540x1080 (left half)
scene.render.resolution_x = 540
scene.render.resolution_y = 1080

# V3 face
aim_camera(0, 8, cam_dist, focus_z, 85)
bpy.context.view_layer.update()
v3_face_path = os.path.join(OUT_DIR, "_v3_face_half.png")
scene.render.filepath = v3_face_path
bpy.ops.render.render(write_still=True)

# V3 silhouette for comparison
for obj in bpy.data.objects:
    if obj.type == 'MESH' and obj.name != "GroundPlane":
        obj.data.materials.clear()
        obj.data.materials.append(sil_mat)
bg.inputs['Color'].default_value = (0.95, 0.95, 0.95, 1.0)
bg.inputs['Strength'].default_value = 1.5
ground.hide_render = True

aim_camera(40, 10, cam_dist, focus_z, 85)
bpy.context.view_layer.update()
v3_sil_path = os.path.join(OUT_DIR, "_v3_sil_half.png")
scene.render.filepath = v3_sil_path
bpy.ops.render.render(write_still=True)

# Create comparison images using Python image compositing
# Load V2 renders and V3 half renders, stitch side by side
import struct

def load_png_via_blender(path):
    """Load image and return (width, height, pixels_list)."""
    img = bpy.data.images.load(path)
    w, h = img.size
    px = list(img.pixels[:])
    bpy.data.images.remove(img)
    return w, h, px

def save_image(path, width, height, pixels):
    """Save pixels as PNG."""
    img = bpy.data.images.new("temp_comp", width=width, height=height, alpha=True)
    img.pixels = pixels
    img.filepath_raw = path
    img.file_format = 'PNG'
    img.save_render(path)
    bpy.data.images.remove(img)

def create_side_by_side(left_path, right_path, output_path, target_w=1080, target_h=1080):
    """Create a side-by-side comparison image."""
    half_w = target_w // 2

    lw, lh, lp = load_png_via_blender(left_path)
    rw, rh, rp = load_png_via_blender(right_path)

    pixels = [0.15, 0.15, 0.15, 1.0] * (target_w * target_h)

    # Place left image
    for y in range(min(target_h, lh)):
        for x in range(min(half_w, lw)):
            si = (y * lw + x) * 4
            di = (y * target_w + x) * 4
            if si + 3 < len(lp):
                pixels[di:di+4] = lp[si:si+4]

    # Place right image
    for y in range(min(target_h, rh)):
        for x in range(min(half_w, rw)):
            si = (y * rw + x) * 4
            di = (y * target_w + (half_w + x)) * 4
            if si + 3 < len(rp):
                pixels[di:di+4] = rp[si:si+4]

    # Draw center divider line
    for y in range(target_h):
        for dx in range(-1, 2):
            x = half_w + dx
            if 0 <= x < target_w:
                di = (y * target_w + x) * 4
                pixels[di:di+4] = [0.8, 0.8, 0.8, 1.0]

    save_image(output_path, target_w, target_h, pixels)
    print(f"  Comparison: {output_path}")

# Create face comparison (V2 left | V3 right)
v2_face = os.path.join(V2_DIR, "front.png")
if os.path.exists(v2_face) and os.path.exists(v3_face_path):
    comp_path = os.path.join(OUT_DIR, "11_v2_vs_v3_face.png")
    create_side_by_side(v2_face, v3_face_path, comp_path)
    rendered["11_v2_vs_v3_face"] = comp_path

# Create silhouette comparison
v2_front = os.path.join(V2_DIR, "front.png")  # Will use V2 front as approximate
if os.path.exists(v2_front) and os.path.exists(v3_sil_path):
    comp_path = os.path.join(OUT_DIR, "12_v2_vs_v3_silhouette.png")
    create_side_by_side(v2_front, v3_sil_path, comp_path)
    rendered["12_v2_vs_v3_silhouette"] = comp_path

# Clean up temp files
for tmp in [v3_face_path, v3_sil_path]:
    if os.path.exists(tmp):
        os.remove(tmp)

# ================================================================
# Contact sheet
# ================================================================
print("\nCreating contact sheet...")

# Reset resolution
scene.render.resolution_x = 1080
scene.render.resolution_y = 1080

# Restore materials for a clean final state
for obj in bpy.data.objects:
    if obj.type == 'MESH' and obj.name in original_mats:
        obj.data.materials.clear()
        for mat in original_mats[obj.name]:
            obj.data.materials.append(mat)
bg.inputs['Color'].default_value = (0.25, 0.24, 0.23, 1.0)
bg.inputs['Strength'].default_value = 1.0
ground.hide_render = False

# Build 4x3 contact sheet from first 12 images
contact_cols = 4
contact_rows = 3
tile_w = 270
tile_h = 270
contact_w = contact_cols * tile_w
contact_h = contact_rows * tile_h

contact_pixels = [0.18, 0.18, 0.18, 1.0] * (contact_w * contact_h)

sheet_views = [
    "01_front", "02_three_quarter", "03_side", "04_back",
    "05_face_closeup", "06_eye_closeup", "07_crest_detail", "08_tail_profile",
    "09_black_silhouette_front", "10_black_silhouette_three_quarter",
]

# Add comparisons if they exist
for extra in ["11_v2_vs_v3_face", "12_v2_vs_v3_silhouette"]:
    if extra in rendered:
        sheet_views.append(extra)

for idx, vname in enumerate(sheet_views[:12]):
    if vname not in rendered:
        continue
    col = idx % contact_cols
    row = (contact_rows - 1) - (idx // contact_cols)  # top to bottom

    try:
        iw, ih, ipx = load_png_via_blender(rendered[vname])
    except:
        continue

    for py in range(tile_h):
        for px in range(tile_w):
            sx = int(px * iw / tile_w)
            sy = int(py * ih / tile_h)
            si = (sy * iw + sx) * 4
            dx = col * tile_w + px
            dy = row * tile_h + py
            di = (dy * contact_w + dx) * 4
            if si + 3 < len(ipx) and di + 3 < len(contact_pixels):
                contact_pixels[di:di+4] = ipx[si:si+4]

contact_path = os.path.join(OUT_DIR, "contact_sheet.png")
save_image(contact_path, contact_w, contact_h, contact_pixels)
rendered["contact_sheet"] = contact_path
print(f"  Contact sheet: {contact_path}")

print(f"\n=== RENDER SET COMPLETE ===")
print(f"Total renders: {len(rendered)}")
for name, path in sorted(rendered.items()):
    fsize = os.path.getsize(path)
    print(f"  {name}: {fsize} bytes")
