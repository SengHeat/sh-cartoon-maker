"""
KIKO 40-Second Visual Review Video
Source: KIKO_source_v3_1.glb (latest clean checkpoint)
960 frames, 24 FPS, 1280x720, Eevee
Continuous smooth camera orbit — no cuts, no animation on model.
"""
import bpy
import bmesh
import os
import math
import time
from mathutils import Vector

PROJECT = "/Users/macbook/Automation-Workplace/cartoon-maker"
SOURCE_GLB = os.path.join(PROJECT, "assets/characters/kiko_final/source/KIKO_source_v3_1.glb")
BLEND_OUT = os.path.join(PROJECT, "projects/characters/kiko/blends/review/KIKO_visual_review_40s.blend")
FRAME_DIR = os.path.join(PROJECT, "output/kiko_visual_review_40s/frames")
MP4_OUT = os.path.join(PROJECT, "output/kiko_visual_review_40s/preview.mp4")
CONTACT_OUT = os.path.join(PROJECT, "output/kiko_visual_review_40s/contact_sheet.jpg")

os.makedirs(FRAME_DIR, exist_ok=True)
os.makedirs(os.path.dirname(BLEND_OUT), exist_ok=True)

start_time = time.time()

# ================================================================
# IMPORT
# ================================================================
print("=== Importing model ===")
bpy.ops.wm.read_homefile(use_empty=True)
bpy.ops.import_scene.gltf(filepath=SOURCE_GLB)
print(f"  Source: {SOURCE_GLB}")

obj_count = len([o for o in bpy.data.objects if o.type == 'MESH'])
vert_count = sum(len(o.data.vertices) for o in bpy.data.objects if o.type == 'MESH')
print(f"  Objects: {obj_count}, Vertices: {vert_count}")

# ================================================================
# MATERIAL VERIFICATION & FIX
# ================================================================
print("\n=== Material check ===")

MATERIAL_COLORS = {
    "Fur | deep teal blue-gray":    ((0.18, 0.28, 0.30, 1), 0.85, 0.0, 0.3),
    "Fur | soft teal highlights":   ((0.30, 0.45, 0.48, 1), 0.80, 0.0, 0.3),
    "Fur | warm integrated cream":  ((0.85, 0.78, 0.65, 1), 0.82, 0.0, 0.3),
    "Fur | pale muzzle":            ((0.90, 0.84, 0.75, 1), 0.80, 0.0, 0.3),
    "Fur | burnt apricot":          ((0.75, 0.40, 0.18, 1), 0.82, 0.0, 0.3),
    "Fur | deep shadow":            ((0.10, 0.15, 0.17, 1), 0.90, 0.0, 0.3),
    "Eye | amber iris":             ((0.85, 0.55, 0.12, 1), 0.12, 0.0, 0.5),
    "Eye | honey iris center":      ((0.95, 0.72, 0.20, 1), 0.08, 0.0, 0.5),
    "Eye | deep warm pupil":        ((0.02, 0.01, 0.01, 1), 0.05, 0.0, 0.5),
    "Eye | soft catchlight":        ((1.0, 1.0, 1.0, 1),    0.00, 0.0, 0.5),
    "Eye | warm ivory":             ((0.95, 0.93, 0.88, 1), 0.20, 0.0, 0.50),
    "Ear | warm coral velvet":      ((0.82, 0.45, 0.35, 1), 0.88, 0.0, 0.3),
    "Nose | rosewood":              ((0.30, 0.15, 0.13, 1), 0.35, 0.0, 0.45),
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

fixed_count = 0
for mat in bpy.data.materials:
    if mat.name in MATERIAL_COLORS and mat.use_nodes:
        base, rough, metal, spec = MATERIAL_COLORS[mat.name]
        for node in mat.node_tree.nodes:
            if node.type == 'BSDF_PRINCIPLED':
                bc = node.inputs['Base Color'].default_value
                is_wrong = (bc[0] > 0.95 and bc[1] > 0.95 and bc[2] > 0.95)
                if is_wrong or mat.name.startswith("Fur") or mat.name.startswith("Cloth") or mat.name.startswith("Leather") or mat.name.startswith("Ear"):
                    node.inputs['Base Color'].default_value = base
                    fixed_count += 1
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
                    try:
                        node.inputs['Emission Color'].default_value = (1, 1, 1, 1)
                        node.inputs['Emission Strength'].default_value = 0.3
                    except:
                        pass

print(f"  Verified/fixed {fixed_count} material base colors")

# Verify key colors
checks = {
    "Fur | deep teal blue-gray": "teal fur",
    "Fur | warm integrated cream": "cream muzzle/chest",
    "Ear | warm coral velvet": "coral inner ears",
    "Eye | amber iris": "amber eyes",
    "Cloth | persimmon scarf": "orange-red scarf",
    "Cloth | worn jungle teal": "green explorer outfit",
    "Leather | worn saddle": "leather accessories",
}
for mat_name, desc in checks.items():
    mat = bpy.data.materials.get(mat_name)
    if mat:
        for node in mat.node_tree.nodes:
            if node.type == 'BSDF_PRINCIPLED':
                bc = node.inputs['Base Color'].default_value
                print(f"  OK {desc}: ({bc[0]:.2f}, {bc[1]:.2f}, {bc[2]:.2f})")

# ================================================================
# CHARACTER BOUNDS
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
mid_z = all_min.z + height * 0.50
face_z = all_min.z + height * 0.80
print(f"\n  Height: {height:.3f}, Center: {center}")

# ================================================================
# SCENE SETUP
# ================================================================
print("\n=== Scene setup ===")
scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 1280
scene.render.resolution_y = 720
scene.render.resolution_percentage = 100
scene.render.film_transparent = False
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGB'
scene.frame_start = 1
scene.frame_end = 960
scene.render.fps = 24

try:
    scene.eevee.taa_render_samples = 48
except:
    pass

# ================================================================
# WORLD — dark charcoal studio gradient
# ================================================================
world = bpy.data.worlds.new("StudioWorld")
scene.world = world
world.use_nodes = True
nodes = world.node_tree.nodes
links = world.node_tree.links
nodes.clear()

# Gradient background: darker at bottom, slightly lighter at top
tex_coord = nodes.new('ShaderNodeTexCoord')
sep_xyz = nodes.new('ShaderNodeSeparateXYZ')
ramp = nodes.new('ShaderNodeValToRGB')
ramp.color_ramp.elements[0].position = 0.0
ramp.color_ramp.elements[0].color = (0.10, 0.10, 0.10, 1.0)  # Dark bottom
ramp.color_ramp.elements[1].position = 1.0
ramp.color_ramp.elements[1].color = (0.22, 0.21, 0.20, 1.0)  # Slightly lighter top

bg = nodes.new('ShaderNodeBackground')
bg.inputs['Strength'].default_value = 1.0
output = nodes.new('ShaderNodeOutputWorld')

links.new(tex_coord.outputs['Generated'], sep_xyz.inputs['Vector'])
links.new(sep_xyz.outputs['Z'], ramp.inputs['Fac'])
links.new(ramp.outputs['Color'], bg.inputs['Color'])
links.new(bg.outputs['Background'], output.inputs['Surface'])

# ================================================================
# GROUND — dark reflective surface
# ================================================================
bpy.ops.mesh.primitive_plane_add(size=40, location=(center.x, center.y, all_min.z - 0.005))
ground = bpy.context.object
ground.name = "StudioFloor"
gmat = bpy.data.materials.new("FloorMat")
gmat.use_nodes = True
bsdf = gmat.node_tree.nodes["Principled BSDF"]
bsdf.inputs["Base Color"].default_value = (0.12, 0.12, 0.12, 1.0)
bsdf.inputs["Roughness"].default_value = 0.70
bsdf.inputs["Metallic"].default_value = 0.0
ground.data.materials.append(gmat)

# ================================================================
# LIGHTING — soft cinematic studio
# ================================================================
print("  Setting up lights...")

def add_area_light(name, loc, energy, size, color, rot=None):
    bpy.ops.object.light_add(type='AREA', location=loc)
    l = bpy.context.object
    l.name = name
    l.data.energy = energy
    l.data.size = size
    l.data.color = color
    if rot:
        l.rotation_euler = rot
    else:
        d = center - Vector(loc)
        l.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    return l

# Key light: soft, warm, upper-right-front
add_area_light("Key",
    (center.x + 3.5, center.y - 5.0, mid_z + 4.0),
    280, 5.0, (1.0, 0.96, 0.90))

# Fill light: cool, left side, very soft
add_area_light("Fill",
    (center.x - 4.0, center.y - 3.0, mid_z + 1.5),
    100, 6.0, (0.85, 0.90, 1.0))

# Rim light: warm, behind and above
add_area_light("Rim",
    (center.x + 0.5, center.y + 4.0, mid_z + 3.5),
    180, 4.0, (1.0, 0.90, 0.80))

# Top hair light: subtle overhead for crest/ears
add_area_light("TopHair",
    (center.x, center.y - 1.0, all_max.z + 3.0),
    80, 3.0, (1.0, 0.97, 0.93))

# Ground bounce: warm uplight
add_area_light("Bounce",
    (center.x, center.y - 2.0, all_min.z - 0.5),
    30, 7.0, (0.92, 0.88, 0.82))

# ================================================================
# CAMERA PATH — continuous smooth orbit
# ================================================================
print("  Building camera path...")

bpy.ops.object.camera_add()
cam = bpy.context.object
cam.name = "ReviewCam"
scene.camera = cam
cam.data.lens = 62  # Moderate telephoto, no wide-angle distortion
cam.data.clip_start = 0.1
cam.data.clip_end = 100

# Camera target (empty that we'll animate for height changes)
bpy.ops.object.empty_add(type='PLAIN_AXES', location=(center.x, center.y, mid_z))
target = bpy.context.object
target.name = "CamTarget"

# Track-To constraint
constraint = cam.constraints.new(type='TRACK_TO')
constraint.target = target
constraint.track_axis = 'TRACK_NEGATIVE_Z'
constraint.up_axis = 'UP_Y'

# Timeline segments (frame ranges):
# 0s-5s   = frames 1-120    FRONT HERO (push in)
# 5s-10s  = frames 121-240  3/4 FRONT (orbit to 40deg)
# 10s-15s = frames 241-360  FACE CLOSE-UP (push to face)
# 15s-20s = frames 361-480  LEFT SIDE (orbit to 90deg)
# 20s-25s = frames 481-600  BACK (orbit to 180deg)
# 25s-30s = frames 601-720  TAIL PROFILE (orbit to ~130deg, lower)
# 30s-35s = frames 721-840  LOW 3/4 HERO (orbit back, low angle)
# 35s-40s = frames 841-960  FINAL BEAUTY (return to 3/4 front, push)

def smooth_interp(t):
    """Smooth ease-in-out interpolation (cosine)."""
    return (1 - math.cos(t * math.pi)) / 2

def lerp(a, b, t):
    return a + (b - a) * t

# Define keyframe data: (frame, angle_deg, elevation_deg, distance, target_z, lens)
# We'll interpolate smoothly between these waypoints
waypoints = [
    # (frame, orbit_angle, elevation, distance, target_z, focal_length)
    (1,    0,    6,   height * 2.4,  mid_z,           62),   # Front hero start
    (120,  0,    8,   height * 2.0,  mid_z,           62),   # Front hero end (pushed in)
    (240,  40,   10,  height * 2.0,  mid_z + 0.15,    62),   # 3/4 front
    (360,  15,   5,   height * 0.85, face_z,          70),   # Face close-up
    (480,  90,   8,   height * 2.0,  mid_z,           62),   # Left side
    (600,  175,  12,  height * 2.2,  mid_z - 0.1,     60),   # Back view
    (720,  130,  2,   height * 1.8,  mid_z - 0.3,     58),   # Tail profile (lower)
    (840,  35,   -2,  height * 2.2,  mid_z - 0.1,     55),   # Low 3/4 hero
    (960,  30,   8,   height * 1.9,  mid_z + 0.1,     62),   # Final beauty
]

# Keyframe camera position at every frame via interpolation
for frame in range(1, 961):
    # Find surrounding waypoints
    wp_before = waypoints[0]
    wp_after = waypoints[-1]
    for i in range(len(waypoints) - 1):
        if waypoints[i][0] <= frame <= waypoints[i + 1][0]:
            wp_before = waypoints[i]
            wp_after = waypoints[i + 1]
            break

    f0 = wp_before[0]
    f1 = wp_after[0]
    if f1 == f0:
        t = 0
    else:
        t = smooth_interp((frame - f0) / (f1 - f0))

    angle = lerp(wp_before[1], wp_after[1], t)
    elev = lerp(wp_before[2], wp_after[2], t)
    dist = lerp(wp_before[3], wp_after[3], t)
    tz = lerp(wp_before[4], wp_after[4], t)
    focal = lerp(wp_before[5], wp_after[5], t)

    # Convert to camera position
    a_rad = math.radians(angle)
    e_rad = math.radians(elev)
    cx = center.x + dist * math.sin(a_rad) * math.cos(e_rad)
    cy = center.y - dist * math.cos(a_rad) * math.cos(e_rad)
    cz = tz + dist * math.sin(e_rad)

    scene.frame_set(frame)
    cam.location = (cx, cy, cz)
    cam.data.lens = focal
    cam.keyframe_insert(data_path="location", frame=frame)
    cam.data.keyframe_insert(data_path="lens", frame=frame)

    target.location = (center.x, center.y, tz)
    target.keyframe_insert(data_path="location", frame=frame)

# Set all keyframe interpolation to smooth (BEZIER)
try:
    for obj in [cam, target]:
        if obj.animation_data and obj.animation_data.action:
            for fcurve in obj.animation_data.action.fcurves:
                for kp in fcurve.keyframe_points:
                    kp.interpolation = 'BEZIER'
                    kp.handle_left_type = 'AUTO_CLAMPED'
                    kp.handle_right_type = 'AUTO_CLAMPED'
    if cam.data.animation_data and cam.data.animation_data.action:
        for fcurve in cam.data.animation_data.action.fcurves:
            for kp in fcurve.keyframe_points:
                kp.interpolation = 'BEZIER'
                kp.handle_left_type = 'AUTO_CLAMPED'
                kp.handle_right_type = 'AUTO_CLAMPED'
    print("  Bezier interpolation applied")
except Exception as e:
    print(f"  Bezier interpolation skipped: {e}")
    print("  (Linear interpolation will be used — still smooth with dense keyframes)")

print("  960 camera keyframes set")

# ================================================================
# SAVE BLEND
# ================================================================
print("\n=== Saving blend ===")
bpy.ops.wm.save_as_mainfile(filepath=BLEND_OUT)
print(f"  {BLEND_OUT}")

# ================================================================
# RENDER FRAMES
# ================================================================
print("\n=== Rendering 960 frames ===")
scene.render.filepath = os.path.join(FRAME_DIR, "frame_")

render_start = time.time()
bpy.ops.render.render(animation=True)
render_time = time.time() - render_start

print(f"  Render time: {render_time:.0f}s ({render_time/60:.1f}m)")

# Verify frame count
import glob
frames = sorted(glob.glob(os.path.join(FRAME_DIR, "frame_*.png")))
print(f"  Frames rendered: {len(frames)}")

total_time = time.time() - start_time
print(f"\n=== RENDER COMPLETE ({total_time:.0f}s total) ===")
print(f"  Frames: {FRAME_DIR}")
print(f"  Blend: {BLEND_OUT}")
