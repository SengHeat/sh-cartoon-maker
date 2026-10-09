"""
Stage 5 — Visual Validation Render v2
Fixed: solid background, material diagnostics, camera verification.
"""
import bpy
import os
import math
import json
from mathutils import Vector

PROJECT = "/Users/macbook/Automation-Workplace/cartoon-maker"
GLB = os.path.join(PROJECT, "assets/characters/kiko_final/source/KIKO_source_v2.glb")
OUT_DIR = os.path.join(PROJECT, "review/kiko_visual")
os.makedirs(OUT_DIR, exist_ok=True)

# --- 1. Clean scene and import ---
bpy.ops.wm.read_homefile(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)

# --- Debug: list all objects and their visibility ---
print("\n=== OBJECT DIAGNOSTICS ===")
mesh_count = 0
for obj in bpy.data.objects:
    if obj.type == 'MESH':
        mesh_count += 1
        if mesh_count <= 5:
            print(f"  Mesh: {obj.name}, visible={not obj.hide_render}, "
                  f"verts={len(obj.data.vertices)}, "
                  f"mats={[m.name for m in obj.data.materials if m]}")
print(f"  ... total {mesh_count} mesh objects")

# --- Debug: check materials ---
print("\n=== MATERIAL DIAGNOSTICS ===")
for mat in bpy.data.materials:
    if mat.use_nodes:
        node_types = [n.type for n in mat.node_tree.nodes]
        print(f"  {mat.name}: nodes={node_types}")
    else:
        print(f"  {mat.name}: no nodes")

# Force all objects visible for render
for obj in bpy.data.objects:
    obj.hide_render = False
    obj.hide_viewport = False

# --- 2. Compute bounds ---
all_min = Vector((float('inf'),) * 3)
all_max = Vector((float('-inf'),) * 3)
for obj in bpy.data.objects:
    if obj.type == 'MESH' and len(obj.data.vertices) > 0:
        for v in obj.data.vertices:
            co = obj.matrix_world @ v.co
            for i in range(3):
                if co[i] < all_min[i]:
                    all_min[i] = co[i]
                if co[i] > all_max[i]:
                    all_max[i] = co[i]

center = (all_min + all_max) / 2
height = all_max.z - all_min.z
focus_z = all_min.z + height * 0.50
face_z = all_min.z + height * 0.82

print(f"\n=== BOUNDS ===")
print(f"Min: {all_min}")
print(f"Max: {all_max}")
print(f"Center: {center}")
print(f"Height: {height:.3f}")

# --- 3. Scene setup ---
scene = bpy.context.scene

# Try available engines
available_engines = ['BLENDER_EEVEE', 'CYCLES', 'BLENDER_WORKBENCH']
for eng in available_engines:
    try:
        scene.render.engine = eng
        print(f"Render engine set to: {eng}")
        break
    except:
        continue

scene.render.resolution_x = 1080
scene.render.resolution_y = 1080
scene.render.resolution_percentage = 100
scene.render.film_transparent = False  # Solid background
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'

# Eevee-specific settings
if scene.render.engine == 'BLENDER_EEVEE':
    try:
        scene.eevee.taa_render_samples = 64
    except:
        pass

# --- 4. World: neutral studio gray ---
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

# --- 5. Three-point lighting ---
cam_dist = height * 2.5

def add_light(name, light_type, location, energy, size=2.0, color=(1, 0.98, 0.95)):
    if light_type == 'AREA':
        bpy.ops.object.light_add(type='AREA', location=location)
        bpy.context.object.data.size = size
    elif light_type == 'SUN':
        bpy.ops.object.light_add(type='SUN', location=location)
    else:
        bpy.ops.object.light_add(type='POINT', location=location)
    light = bpy.context.object
    light.name = name
    light.data.energy = energy
    light.data.color = color
    # Point light at character center
    direction = center - Vector(location)
    light.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
    return light

# Key light: upper right
add_light("Key", "AREA",
          (center.x + cam_dist * 0.7, center.y - cam_dist * 0.8, focus_z + height * 0.8),
          energy=500, size=4.0, color=(1.0, 0.97, 0.92))

# Fill light: left side, cooler
add_light("Fill", "AREA",
          (center.x - cam_dist * 0.8, center.y - cam_dist * 0.5, focus_z + height * 0.2),
          energy=200, size=5.0, color=(0.88, 0.92, 1.0))

# Rim light: behind
add_light("Rim", "AREA",
          (center.x, center.y + cam_dist * 0.8, focus_z + height * 0.6),
          energy=350, size=3.0, color=(1.0, 0.92, 0.82))

# Bottom fill
add_light("Bounce", "AREA",
          (center.x, center.y - cam_dist * 0.3, all_min.z - 0.3),
          energy=60, size=6.0, color=(0.95, 0.92, 0.88))

# --- 6. Ground plane ---
bpy.ops.mesh.primitive_plane_add(size=30, location=(center.x, center.y, all_min.z - 0.005))
ground = bpy.context.object
ground.name = "GroundPlane"
mat_ground = bpy.data.materials.new("GroundMat")
mat_ground.use_nodes = True
bsdf = mat_ground.node_tree.nodes["Principled BSDF"]
bsdf.inputs["Base Color"].default_value = (0.30, 0.29, 0.28, 1.0)
bsdf.inputs["Roughness"].default_value = 0.85
ground.data.materials.append(mat_ground)

# --- 7. Camera ---
bpy.ops.object.camera_add()
cam_obj = bpy.context.object
cam_obj.name = "ValidationCam"
scene.camera = cam_obj

def aim_camera(angle_deg, elevation_deg, distance, target_z, lens=85):
    """Position camera orbiting character center at angle/elevation."""
    angle = math.radians(angle_deg)
    elev = math.radians(elevation_deg)

    # Camera position in spherical coords around character
    cx = center.x + distance * math.sin(angle) * math.cos(elev)
    cy = center.y - distance * math.cos(angle) * math.cos(elev)
    cz = target_z + distance * math.sin(elev)

    cam_obj.location = (cx, cy, cz)
    cam_obj.data.lens = lens

    # Use track-to constraint for reliable aiming
    # Remove old constraints first
    for c in cam_obj.constraints:
        cam_obj.constraints.remove(c)

    # Create an empty at the target point
    target_name = "CamTarget"
    target = bpy.data.objects.get(target_name)
    if not target:
        bpy.ops.object.empty_add(type='PLAIN_AXES', location=(center.x, center.y, target_z))
        target = bpy.context.object
        target.name = target_name
    else:
        target.location = (center.x, center.y, target_z)

    constraint = cam_obj.constraints.new(type='TRACK_TO')
    constraint.target = target
    constraint.track_axis = 'TRACK_NEGATIVE_Z'
    constraint.up_axis = 'UP_Y'

    print(f"  Camera at ({cx:.2f}, {cy:.2f}, {cz:.2f}), lens={lens}, target_z={target_z:.2f}")

# --- 8. Render each view ---
views = [
    # (name, angle_deg, elevation_deg, distance, target_z, lens)
    ("front",         0,   8,  cam_dist,       focus_z,  85),
    ("three_quarter", 40,  10, cam_dist,       focus_z,  85),
    ("side",          90,  8,  cam_dist,       focus_z,  85),
    ("back",          180, 10, cam_dist,       focus_z,  85),
    ("face_closeup",  8,   3,  height * 0.75,  face_z,   100),
]

rendered = {}
for name, angle, elev, dist, tz, lens in views:
    print(f"\nRendering {name}...")
    aim_camera(angle, elev, dist, tz, lens)

    # Force scene update
    bpy.context.view_layer.update()

    filepath = os.path.join(OUT_DIR, f"{name}.png")
    scene.render.filepath = filepath
    bpy.ops.render.render(write_still=True)
    rendered[name] = filepath

    # Check output file size
    if os.path.exists(filepath):
        fsize = os.path.getsize(filepath)
        print(f"  -> {filepath} ({fsize} bytes)")
    else:
        print(f"  -> MISSING!")

# --- 9. Contact sheet via Python (no ImageMagick needed) ---
print("\nCreating contact sheet...")
try:
    # Load all rendered images and composite them
    # Using Blender's image compositor
    contact_w = 1620  # 3 cols x 540
    contact_h = 1080  # 2 rows x 540
    tile_w = 540
    tile_h = 540

    contact = bpy.data.images.new("ContactSheet", width=contact_w, height=contact_h, alpha=True)
    pixels = [0.2, 0.2, 0.2, 1.0] * (contact_w * contact_h)

    view_order = ["front", "three_quarter", "side", "back", "face_closeup"]
    positions = [(0, 1), (1, 1), (2, 1), (0, 0), (1, 0)]  # (col, row) - row 0 is bottom

    for idx, vname in enumerate(view_order):
        img = bpy.data.images.load(rendered[vname])
        iw, ih = img.size
        col, row = positions[idx]
        src_pixels = list(img.pixels)

        for py in range(tile_h):
            for px in range(tile_w):
                # Sample from source
                sx = int(px * iw / tile_w)
                sy = int(py * ih / tile_h)
                si = (sy * iw + sx) * 4
                # Destination
                dx = col * tile_w + px
                dy = row * tile_h + py
                di = (dy * contact_w + dx) * 4
                if si + 3 < len(src_pixels) and di + 3 < len(pixels):
                    pixels[di] = src_pixels[si]
                    pixels[di + 1] = src_pixels[si + 1]
                    pixels[di + 2] = src_pixels[si + 2]
                    pixels[di + 3] = src_pixels[si + 3]

        bpy.data.images.remove(img)

    contact.pixels = pixels
    contact_path = os.path.join(OUT_DIR, "contact_sheet.jpg")
    contact.filepath_raw = contact_path
    contact.file_format = 'JPEG'
    contact.save_render(contact_path)
    bpy.data.images.remove(contact)
    print(f"Contact sheet: {contact_path}")
except Exception as e:
    print(f"Contact sheet error: {e}")
    import traceback
    traceback.print_exc()

print("\n=== STAGE 5 VALIDATION RENDERS COMPLETE ===")
for name, path in rendered.items():
    print(f"  {name}: {path}")
