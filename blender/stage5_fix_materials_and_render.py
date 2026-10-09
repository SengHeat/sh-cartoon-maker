"""
Stage 5 — Fix materials from GLB import and re-render validation views.
The GLB materials imported as white Principled BSDF. Apply correct colors
based on the descriptive material names, then render all views.
"""
import bpy
import os
import math
from mathutils import Vector

PROJECT = "/Users/macbook/Automation-Workplace/cartoon-maker"
GLB = os.path.join(PROJECT, "assets/characters/kiko_final/source/KIKO_source_v2.glb")
OUT_DIR = os.path.join(PROJECT, "review/kiko_visual")
os.makedirs(OUT_DIR, exist_ok=True)

# --- 1. Clean scene and import ---
bpy.ops.wm.read_homefile(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)

# --- 2. Diagnose current material colors ---
print("\n=== CURRENT MATERIAL BASE COLORS ===")
for mat in bpy.data.materials:
    if mat.use_nodes:
        for node in mat.node_tree.nodes:
            if node.type == 'BSDF_PRINCIPLED':
                bc = node.inputs['Base Color'].default_value
                metal = node.inputs['Metallic'].default_value
                rough = node.inputs['Roughness'].default_value
                print(f"  {mat.name}: BaseColor=({bc[0]:.3f}, {bc[1]:.3f}, {bc[2]:.3f}), "
                      f"Metal={metal:.2f}, Rough={rough:.2f}")

# --- 3. Define correct colors from KIKO concept art ---
# Colors derived from the authoritative reference images
MATERIAL_COLORS = {
    # Fur colors
    "Fur | deep teal blue-gray": {
        "base": (0.18, 0.28, 0.30, 1.0),  # Dark teal-gray
        "roughness": 0.85,
        "metallic": 0.0,
    },
    "Fur | soft teal highlights": {
        "base": (0.30, 0.45, 0.48, 1.0),  # Lighter teal
        "roughness": 0.80,
        "metallic": 0.0,
    },
    "Fur | warm integrated cream": {
        "base": (0.85, 0.78, 0.65, 1.0),  # Warm cream
        "roughness": 0.82,
        "metallic": 0.0,
    },
    "Fur | pale muzzle": {
        "base": (0.90, 0.84, 0.75, 1.0),  # Light cream/pale
        "roughness": 0.80,
        "metallic": 0.0,
    },
    "Fur | burnt apricot": {
        "base": (0.75, 0.40, 0.18, 1.0),  # Orange-brown spots/accents
        "roughness": 0.82,
        "metallic": 0.0,
    },
    "Fur | deep shadow": {
        "base": (0.10, 0.15, 0.17, 1.0),  # Dark shadow fur
        "roughness": 0.90,
        "metallic": 0.0,
    },

    # Eye colors
    "Eye | amber iris": {
        "base": (0.85, 0.55, 0.12, 1.0),  # Rich amber
        "roughness": 0.15,
        "metallic": 0.0,
    },
    "Eye | honey iris center": {
        "base": (0.95, 0.72, 0.20, 1.0),  # Bright honey gold
        "roughness": 0.10,
        "metallic": 0.0,
    },
    "Eye | deep warm pupil": {
        "base": (0.02, 0.01, 0.01, 1.0),  # Near black
        "roughness": 0.05,
        "metallic": 0.0,
    },
    "Eye | soft catchlight": {
        "base": (1.0, 1.0, 1.0, 1.0),  # Pure white glint
        "roughness": 0.0,
        "metallic": 0.0,
        "emission": (1.0, 1.0, 1.0),
        "emission_strength": 0.5,
    },
    "Eye | warm ivory": {
        "base": (0.95, 0.93, 0.88, 1.0),  # Warm white sclera
        "roughness": 0.25,
        "metallic": 0.0,
    },

    # Ear
    "Ear | warm coral velvet": {
        "base": (0.82, 0.45, 0.35, 1.0),  # Warm orange-pink
        "roughness": 0.90,
        "metallic": 0.0,
    },

    # Nose
    "Nose | rosewood": {
        "base": (0.30, 0.15, 0.13, 1.0),  # Dark rosewood
        "roughness": 0.40,
        "metallic": 0.0,
    },

    # Mouth
    "Mouth | warm dark umber": {
        "base": (0.20, 0.10, 0.08, 1.0),  # Dark mouth interior
        "roughness": 0.70,
        "metallic": 0.0,
    },

    # Cloth
    "Cloth | worn jungle teal": {
        "base": (0.22, 0.32, 0.30, 1.0),  # Worn teal vest
        "roughness": 0.85,
        "metallic": 0.0,
    },
    "Cloth | faded olive panels": {
        "base": (0.35, 0.38, 0.25, 1.0),  # Faded olive green
        "roughness": 0.88,
        "metallic": 0.0,
    },
    "Cloth | persimmon scarf": {
        "base": (0.80, 0.30, 0.12, 1.0),  # Orange-red scarf
        "roughness": 0.75,
        "metallic": 0.0,
    },
    "Cloth | scarf highlights": {
        "base": (0.88, 0.42, 0.18, 1.0),  # Lighter scarf accent
        "roughness": 0.72,
        "metallic": 0.0,
    },

    # Leather
    "Leather | dark walnut": {
        "base": (0.22, 0.13, 0.08, 1.0),  # Dark brown leather
        "roughness": 0.65,
        "metallic": 0.0,
    },
    "Leather | worn saddle": {
        "base": (0.42, 0.28, 0.15, 1.0),  # Medium brown leather
        "roughness": 0.60,
        "metallic": 0.0,
    },

    # Hardware
    "Hardware | aged brass": {
        "base": (0.72, 0.58, 0.22, 1.0),  # Aged brass/gold
        "roughness": 0.35,
        "metallic": 0.85,
    },

    # Thread
    "Thread | flax": {
        "base": (0.70, 0.62, 0.45, 1.0),  # Natural flax thread
        "roughness": 0.90,
        "metallic": 0.0,
    },
}

# --- 4. Apply colors ---
print("\n=== APPLYING CORRECTED COLORS ===")
for mat in bpy.data.materials:
    if mat.name in MATERIAL_COLORS and mat.use_nodes:
        props = MATERIAL_COLORS[mat.name]
        for node in mat.node_tree.nodes:
            if node.type == 'BSDF_PRINCIPLED':
                node.inputs['Base Color'].default_value = props["base"]
                node.inputs['Roughness'].default_value = props["roughness"]
                node.inputs['Metallic'].default_value = props["metallic"]
                if "emission" in props:
                    node.inputs['Emission Color'].default_value = (*props["emission"], 1.0)
                    node.inputs['Emission Strength'].default_value = props["emission_strength"]
                print(f"  Applied: {mat.name}")
    elif mat.name not in MATERIAL_COLORS:
        print(f"  UNMAPPED: {mat.name}")

# Force all objects visible
for obj in bpy.data.objects:
    obj.hide_render = False
    obj.hide_viewport = False

# --- 5. Compute bounds ---
all_min = Vector((float('inf'),) * 3)
all_max = Vector((float('-inf'),) * 3)
for obj in bpy.data.objects:
    if obj.type == 'MESH' and len(obj.data.vertices) > 0:
        for v in obj.data.vertices:
            co = obj.matrix_world @ v.co
            for i in range(3):
                if co[i] < all_min[i]: all_min[i] = co[i]
                if co[i] > all_max[i]: all_max[i] = co[i]

center = (all_min + all_max) / 2
height = all_max.z - all_min.z
focus_z = all_min.z + height * 0.50
face_z = all_min.z + height * 0.82

# --- 6. Scene setup ---
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

# --- 7. Studio lighting ---
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
    return light

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

# --- 8. Camera ---
bpy.ops.object.camera_add()
cam_obj = bpy.context.object
cam_obj.name = "ValidationCam"
scene.camera = cam_obj

# Create target empty
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

# --- 9. Render views ---
views = [
    ("front",         0,   8,  cam_dist,       focus_z,  85),
    ("three_quarter", 40,  10, cam_dist,       focus_z,  85),
    ("side",          90,  8,  cam_dist,       focus_z,  85),
    ("back",          180, 10, cam_dist,       focus_z,  85),
    ("face_closeup",  8,   3,  height * 0.75,  face_z,   100),
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

print("\n=== STAGE 5 VALIDATION RENDERS (COLORED) COMPLETE ===")
for name, path in rendered.items():
    print(f"  {name}: {path}")
