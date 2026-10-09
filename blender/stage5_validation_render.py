"""
Stage 5 — Visual Validation Render
Imports KIKO_source_v2.glb, sets up neutral studio lighting,
and renders front / 3-4 / side / back / face closeup views.
"""
import bpy
import os
import math
import json

PROJECT = "/Users/macbook/Automation-Workplace/cartoon-maker"
GLB = os.path.join(PROJECT, "assets/characters/kiko_final/source/KIKO_source_v2.glb")
OUT_DIR = os.path.join(PROJECT, "review/kiko_visual")
os.makedirs(OUT_DIR, exist_ok=True)

# --- 1. Clean scene and import ---
bpy.ops.wm.read_homefile(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)

# Find bounds of all mesh objects
all_min = [float('inf')] * 3
all_max = [float('-inf')] * 3
for obj in bpy.data.objects:
    if obj.type == 'MESH':
        for v in obj.data.vertices:
            co = obj.matrix_world @ v.co
            for i in range(3):
                all_min[i] = min(all_min[i], co[i])
                all_max[i] = max(all_max[i], co[i])

center_x = (all_min[0] + all_max[0]) / 2
center_y = (all_min[1] + all_max[1]) / 2
center_z = (all_min[2] + all_max[2]) / 2
height = all_max[2] - all_min[2]

# Focus point: chest area (roughly 60% up)
focus_z = all_min[2] + height * 0.55
# Face focus: roughly 85% up
face_z = all_min[2] + height * 0.80

print(f"Character bounds: min={all_min}, max={all_max}")
print(f"Center: ({center_x:.3f}, {center_y:.3f}, {center_z:.3f}), height: {height:.3f}")
print(f"Focus Z: {focus_z:.3f}, Face Z: {face_z:.3f}")

# --- 2. Neutral studio environment ---
scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 1080
scene.render.resolution_y = 1080
scene.render.resolution_percentage = 100
scene.render.film_transparent = True
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'

# Eevee settings
eevee = scene.eevee
eevee.taa_render_samples = 64

# World: neutral warm gray gradient
world = bpy.data.worlds.new("StudioWorld")
scene.world = world
world.use_nodes = True
nodes = world.node_tree.nodes
links = world.node_tree.links
nodes.clear()

bg = nodes.new('ShaderNodeBackground')
bg.inputs['Color'].default_value = (0.28, 0.27, 0.26, 1.0)
bg.inputs['Strength'].default_value = 0.5

output = nodes.new('ShaderNodeOutputWorld')
links.new(bg.outputs['Background'], output.inputs['Surface'])

# --- 3. Three-point studio lighting ---
# Camera distance for full body
cam_dist = height * 2.2

def add_area_light(name, location, rotation, energy, size, color=(1.0, 0.98, 0.95)):
    bpy.ops.object.light_add(type='AREA', location=location)
    light = bpy.context.object
    light.name = name
    light.rotation_euler = rotation
    light.data.energy = energy
    light.data.size = size
    light.data.color = color
    return light

# Key light: warm, upper right front
key_angle = math.radians(40)
key_elev = math.radians(35)
key_dist = cam_dist * 1.5
key_x = center_x + key_dist * math.sin(key_angle) * math.cos(key_elev)
key_y = center_y - key_dist * math.cos(key_angle) * math.cos(key_elev)
key_z = focus_z + key_dist * math.sin(key_elev)
add_area_light("Key", (key_x, key_y, key_z),
               (math.radians(50), 0, math.radians(40)),
               energy=300, size=3.0, color=(1.0, 0.97, 0.92))

# Fill light: cool, left side, softer
fill_angle = math.radians(-50)
fill_dist = cam_dist * 1.8
fill_x = center_x + fill_dist * math.sin(fill_angle)
fill_y = center_y - fill_dist * math.cos(fill_angle)
fill_z = focus_z + height * 0.1
add_area_light("Fill", (fill_x, fill_y, fill_z),
               (math.radians(80), 0, math.radians(-50)),
               energy=120, size=4.0, color=(0.88, 0.92, 1.0))

# Rim/back light: warm accent from behind
rim_x = center_x - 0.5
rim_y = center_y + cam_dist * 1.0
rim_z = focus_z + height * 0.5
add_area_light("Rim", (rim_x, rim_y, rim_z),
               (math.radians(120), 0, math.radians(180)),
               energy=200, size=2.0, color=(1.0, 0.90, 0.80))

# Ground bounce: subtle warm uplight
bounce_z = all_min[2] - 0.2
add_area_light("Bounce", (center_x, center_y, bounce_z),
               (math.radians(-90), 0, 0),
               energy=30, size=5.0, color=(0.95, 0.90, 0.85))

# --- 4. Ground plane (neutral gray) ---
bpy.ops.mesh.primitive_plane_add(size=20, location=(center_x, center_y, all_min[2] - 0.01))
ground = bpy.context.object
ground.name = "GroundPlane"
mat_ground = bpy.data.materials.new("GroundMat")
mat_ground.use_nodes = True
bsdf = mat_ground.node_tree.nodes["Principled BSDF"]
bsdf.inputs["Base Color"].default_value = (0.32, 0.31, 0.30, 1.0)
bsdf.inputs["Roughness"].default_value = 0.9
ground.data.materials.append(mat_ground)

# --- 5. Camera setup and render views ---
bpy.ops.object.camera_add()
cam_obj = bpy.context.object
cam_obj.name = "ValidationCam"
scene.camera = cam_obj
cam_obj.data.lens = 85  # Portrait lens for character renders

def set_camera(angle_deg, elevation_deg, distance, target_z, lens=85):
    """Position camera orbiting around center_x, center_y at given angle/elevation."""
    angle = math.radians(angle_deg)
    elev = math.radians(elevation_deg)
    x = center_x + distance * math.sin(angle) * math.cos(elev)
    y = center_y - distance * math.cos(angle) * math.cos(elev)
    z = target_z + distance * math.sin(elev)
    cam_obj.location = (x, y, z)
    cam_obj.data.lens = lens

    # Point at target
    direction = (center_x - x, center_y - y, target_z - z)
    rot_z = math.atan2(direction[0], -direction[1])
    dist_h = math.sqrt(direction[0]**2 + direction[1]**2)
    rot_x = math.atan2(-direction[2], dist_h) + math.pi/2
    cam_obj.rotation_euler = (rot_x, 0, rot_z)


views = [
    # (name, angle_deg, elevation_deg, distance, target_z, lens)
    ("front",         0,   8, cam_dist, focus_z, 85),
    ("three_quarter", 35,  10, cam_dist, focus_z, 85),
    ("side",          90,  8, cam_dist, focus_z, 85),
    ("back",          180, 10, cam_dist, focus_z, 85),
    ("face_closeup",  5,   5, height * 0.9, face_z, 100),
]

rendered = {}
for name, angle, elev, dist, tz, lens in views:
    set_camera(angle, elev, dist, tz, lens)
    filepath = os.path.join(OUT_DIR, f"{name}.png")
    scene.render.filepath = filepath
    bpy.ops.render.render(write_still=True)
    rendered[name] = filepath
    print(f"Rendered: {name} -> {filepath}")

# --- 6. Create contact sheet (composited in Blender) ---
# Use Python/compositor to combine images
import subprocess

contact_path = os.path.join(OUT_DIR, "contact_sheet.jpg")
# Use ImageMagick montage if available, otherwise use Blender compositor
try:
    imgs = [rendered[v] for v in ["front", "three_quarter", "side", "back", "face_closeup"]]
    cmd = [
        "montage",
        *imgs,
        "-tile", "3x2",
        "-geometry", "540x540+4+4",
        "-background", "#444444",
        contact_path
    ]
    subprocess.run(cmd, check=True)
    print(f"Contact sheet created: {contact_path}")
except Exception as e:
    print(f"ImageMagick not available for contact sheet: {e}")
    # Fallback: just copy front as placeholder
    import shutil
    shutil.copy(rendered["front"], contact_path)
    print(f"Contact sheet fallback (front only): {contact_path}")

print("\n=== STAGE 5 VALIDATION RENDERS COMPLETE ===")
for name, path in rendered.items():
    print(f"  {name}: {path}")
print(f"  contact_sheet: {contact_path}")
