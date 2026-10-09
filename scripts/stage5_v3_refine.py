"""
Stage 5.1 — Targeted KIKO Visual Refinement
Imports V2 GLB, applies localized geometry + material fixes, exports V3.
Does NOT rebuild from scratch. Modifies existing objects in-place.
"""
import bpy
import bmesh
import os
import math
import json
from mathutils import Vector, Matrix, Euler
import random

random.seed(42)  # Deterministic

PROJECT = "/Users/macbook/Automation-Workplace/cartoon-maker"
GLB_V2 = os.path.join(PROJECT, "assets/characters/kiko_final/source/KIKO_source_v2.glb")
GLB_V3 = os.path.join(PROJECT, "assets/characters/kiko_final/source/KIKO_source_v3.glb")
BLEND_V3 = os.path.join(PROJECT, "projects/characters/kiko/blends/master/KIKO_visual_stage5_v3.blend")

# ================================================================
# PHASE 0 — Import V2
# ================================================================
print("\n=== PHASE 0: Import V2 ===")
bpy.ops.wm.read_homefile(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB_V2)

# Deselect all
bpy.ops.object.select_all(action='DESELECT')

# Build lookup
obj_map = {}
for obj in bpy.data.objects:
    obj_map[obj.name] = obj

print(f"Imported {len(obj_map)} objects")

# Compute character bounds
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
print(f"Character height: {height:.3f}, center: {center}")

# ================================================================
# Helper functions
# ================================================================

def get_obj(name):
    """Get object by name."""
    return obj_map.get(name)

def get_mesh_center(obj):
    """Get world-space center of mesh bounding box."""
    verts = [obj.matrix_world @ v.co for v in obj.data.vertices]
    if not verts:
        return obj.location.copy()
    mn = verts[0].copy()
    mx = verts[0].copy()
    for v in verts:
        for i in range(3):
            mn[i] = min(mn[i], v[i])
            mx[i] = max(mx[i], v[i])
    return (mn + mx) / 2

def scale_object_from_center(obj, scale_factors):
    """Scale an object's mesh around its own center in world space."""
    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)

    # Get center in local space
    local_verts = [v.co.copy() for v in bm.verts]
    if not local_verts:
        bm.free()
        return
    center_local = sum(local_verts, Vector((0,0,0))) / len(local_verts)

    for v in bm.verts:
        offset = v.co - center_local
        v.co = center_local + Vector((
            offset.x * scale_factors[0],
            offset.y * scale_factors[1],
            offset.z * scale_factors[2]
        ))

    bm.to_mesh(me)
    bm.free()
    me.update()

def displace_verts_outward(obj, amount, falloff_axis=None, falloff_center=0, falloff_range=1):
    """Push vertices outward from mesh center by amount."""
    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.normal_update()

    for v in bm.verts:
        if v.normal.length < 0.001:
            continue
        factor = amount
        if falloff_axis is not None:
            dist = abs(v.co[falloff_axis] - falloff_center) / max(falloff_range, 0.001)
            factor *= max(0, 1.0 - dist)
        v.co += v.normal * factor

    bm.to_mesh(me)
    bm.free()
    me.update()

def add_fur_clump(name, base_obj, local_pos, direction, length, width, taper=0.3,
                  twist_deg=0, material_name=None):
    """Create a single stylized fur clump (tapered elongated shape)."""
    # Create a cone-like shape using a cylinder with tapered top
    bpy.ops.mesh.primitive_cone_add(
        vertices=8,
        radius1=width,
        radius2=width * taper,
        depth=length,
        location=(0, 0, 0)
    )
    clump = bpy.context.object
    clump.name = name

    # Smooth shade
    for poly in clump.data.polygons:
        poly.use_smooth = True

    # Apply subdivision for softness
    mod = clump.modifiers.new("Smooth", 'SUBSURF')
    mod.levels = 1
    mod.render_levels = 1
    bpy.context.view_layer.objects.active = clump
    bpy.ops.object.modifier_apply(modifier="Smooth")

    # Orient along direction
    dir_vec = Vector(direction).normalized()
    up = Vector((0, 0, 1))
    rot_quat = up.rotation_difference(dir_vec)

    # Apply twist
    if twist_deg != 0:
        twist_quat = dir_vec.to_track_quat('Z', 'Y')
        # Just add euler twist

    # Position relative to base object
    world_pos = base_obj.matrix_world @ Vector(local_pos)
    clump.location = world_pos
    clump.rotation_euler = rot_quat.to_euler()

    # Apply material
    if material_name and material_name in bpy.data.materials:
        clump.data.materials.append(bpy.data.materials[material_name])

    # Add to obj_map
    obj_map[name] = clump
    return clump

def create_fur_mass(name, center_pos, scale, direction, material_name,
                    subdivisions=2, noise_strength=0.0):
    """Create a broad fur mass using a deformed sphere."""
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=12, ring_count=8,
        radius=1.0,
        location=center_pos
    )
    mass = bpy.context.object
    mass.name = name
    mass.scale = scale

    # Orient
    if direction:
        dir_vec = Vector(direction).normalized()
        up = Vector((0, 0, 1))
        rot_quat = up.rotation_difference(dir_vec)
        mass.rotation_euler = rot_quat.to_euler()

    # Apply transforms
    bpy.context.view_layer.objects.active = mass
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

    # Subdivide
    if subdivisions > 0:
        mod = mass.modifiers.new("Sub", 'SUBSURF')
        mod.levels = subdivisions
        mod.render_levels = subdivisions
        bpy.ops.object.modifier_apply(modifier="Sub")

    # Add noise for organic feel
    if noise_strength > 0:
        me = mass.data
        bm = bmesh.new()
        bm.from_mesh(me)
        for v in bm.verts:
            n = v.normal
            noise_val = (random.random() - 0.5) * 2 * noise_strength
            v.co += n * noise_val
        bm.to_mesh(me)
        bm.free()
        me.update()

    # Smooth shade
    for poly in mass.data.polygons:
        poly.use_smooth = True

    # Material
    if material_name and material_name in bpy.data.materials:
        mass.data.materials.append(bpy.data.materials[material_name])

    obj_map[name] = mass
    return mass


# ================================================================
# PHASE 1 — CHEEK REFINEMENT (Target 1 + 2)
# ================================================================
print("\n=== PHASE 1: Cheek Refinement ===")

# Get reference objects
body = get_obj("KIKO | continuous sculpted body, head and ears")
cheek_muzzle = get_obj("KIKO | integrated cream cheeks and muzzle")

# Current cheek tufts to scale up
cheek_tufts_L = [
    get_obj("KIKO | cheek tuft L 1"),
    get_obj("KIKO | cheek tuft L 2"),
    get_obj("KIKO | cheek tuft L 3"),
]
cheek_tufts_R = [
    get_obj("KIKO | cheek tuft R 1"),
    get_obj("KIKO | cheek tuft R 2"),
    get_obj("KIKO | cheek tuft R 3"),
]

# Scale up existing cheek tufts significantly
for tuft in cheek_tufts_L + cheek_tufts_R:
    if tuft:
        scale_object_from_center(tuft, (1.8, 1.6, 1.7))
        # Also push outward slightly
        displace_verts_outward(tuft, 0.02)
        print(f"  Scaled up: {tuft.name}")

# Expand the cheek/muzzle mesh outward at the cheek region
if cheek_muzzle:
    me = cheek_muzzle.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.normal_update()

    # Get mesh center for reference
    cheek_center = get_mesh_center(cheek_muzzle)
    head_center_z = all_min.z + height * 0.82  # approximate head center

    # Push cheek vertices outward, stronger at sides
    for v in bm.verts:
        world_co = cheek_muzzle.matrix_world @ v.co

        # Only affect vertices in the cheek zone (roughly mid-face height)
        z_rel = (world_co.z - (head_center_z - 0.5)) / 1.0
        if 0.1 < z_rel < 0.8:  # cheek zone
            # Lateral expansion - push X outward from center
            x_offset = world_co.x - center.x
            if abs(x_offset) > 0.15:  # only sides, not center muzzle
                lateral_factor = min(abs(x_offset) / 0.5, 1.0) * 0.12
                sign = 1 if x_offset > 0 else -1
                # Convert to local space displacement
                local_dir = cheek_muzzle.matrix_world.inverted().to_3x3() @ Vector((sign, 0, 0))
                v.co += local_dir * lateral_factor

            # Slight forward push for volume
            if v.normal.length > 0.001:
                v.co += v.normal * 0.03

    bm.to_mesh(me)
    bm.free()
    me.update()
    print("  Expanded cheek/muzzle volume")

# Add large fur masses at cheek sides for dramatic silhouette
# These are broad, layered shapes - NOT spikes
cheek_masses_added = 0

# Head center estimate from the body mesh
head_z = all_min.z + height * 0.78

# LEFT cheek - large fur masses
for i, (y_off, z_off, sx, sy, sz, rot_z) in enumerate([
    (-0.08, -0.05, 0.22, 0.14, 0.18, -15),   # Lower main mass
    (-0.04, 0.08, 0.20, 0.12, 0.15, -25),    # Upper mass
    (-0.10, 0.02, 0.16, 0.10, 0.22, -5),     # Side mass
]):
    pos = (center.x + 0.55 + i * 0.03, center.y + y_off, head_z + z_off)
    mass = create_fur_mass(
        f"KIKO | cheek fur mass L {i+1}",
        pos,
        scale=(sx, sy, sz),
        direction=(1.0, -0.3, -0.2),
        material_name="Fur | warm integrated cream",
        subdivisions=2,
        noise_strength=0.015
    )
    mass.rotation_euler.z += math.radians(rot_z)
    cheek_masses_added += 1

# RIGHT cheek - mirror
for i, (y_off, z_off, sx, sy, sz, rot_z) in enumerate([
    (-0.08, -0.05, 0.22, 0.14, 0.18, 15),
    (-0.04, 0.08, 0.20, 0.12, 0.15, 25),
    (-0.10, 0.02, 0.16, 0.10, 0.22, 5),
]):
    pos = (center.x - 0.55 - i * 0.03, center.y + y_off, head_z + z_off)
    mass = create_fur_mass(
        f"KIKO | cheek fur mass R {i+1}",
        pos,
        scale=(sx, sy, sz),
        direction=(-1.0, -0.3, -0.2),
        material_name="Fur | warm integrated cream",
        subdivisions=2,
        noise_strength=0.015
    )
    mass.rotation_euler.z += math.radians(rot_z)
    cheek_masses_added += 1

# Add some slightly darker accent tufts at cheek edges
for side, sign in [("L", 1), ("R", -1)]:
    for j in range(2):
        z_off = -0.08 + j * 0.14
        pos = (center.x + sign * 0.65, center.y - 0.06, head_z + z_off)
        mass = create_fur_mass(
            f"KIKO | cheek edge tuft {side} {j+1}",
            pos,
            scale=(0.10, 0.07, 0.12),
            direction=(sign * 0.8, -0.5, -0.3),
            material_name="Fur | warm integrated cream",
            subdivisions=1,
            noise_strength=0.01
        )
        cheek_masses_added += 1

print(f"  Added {cheek_masses_added} cheek fur masses")

# Also expand freckle spots slightly outward so they sit on enlarged cheeks
for name in ["KIKO | cheek freckle L 1", "KIKO | cheek freckle L 2", "KIKO | cheek freckle L 3",
             "KIKO | cheek freckle R 1", "KIKO | cheek freckle R 2", "KIKO | cheek freckle R 3"]:
    obj = get_obj(name)
    if obj:
        # Move slightly outward
        c = get_mesh_center(obj)
        offset_dir = (c - center).normalized()
        obj.location += offset_dir * 0.06


# ================================================================
# PHASE 2 — CREST REFINEMENT (Target 3)
# ================================================================
print("\n=== PHASE 2: Crest Refinement ===")

crest_locks = []
for i in range(1, 11):
    name = f"KIKO | layered crest lock {i:02d}"
    obj = get_obj(name)
    if obj:
        crest_locks.append(obj)

for idx, lock in enumerate(crest_locks):
    me = lock.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.normal_update()

    # Get local bounds
    local_verts = [v.co.copy() for v in bm.verts]
    if not local_verts:
        bm.free()
        continue

    min_z = min(v.z for v in local_verts)
    max_z = max(v.z for v in local_verts)
    z_range = max_z - min_z
    center_local = sum(local_verts, Vector((0,0,0))) / len(local_verts)

    # Vary each lock differently
    seed_val = idx * 7 + 3
    random.seed(seed_val)

    for v in bm.verts:
        t = (v.co.z - min_z) / max(z_range, 0.001)  # 0=base, 1=tip

        # 1. Widen root (t < 0.3): expand laterally
        if t < 0.35:
            root_factor = (0.35 - t) / 0.35
            offset = v.co - center_local
            # Expand X and Y at root
            v.co.x += offset.x * root_factor * 0.25
            v.co.y += offset.y * root_factor * 0.20

        # 2. Taper tip more (t > 0.6): narrow
        if t > 0.55:
            tip_factor = (t - 0.55) / 0.45
            offset = v.co - center_local
            taper = 1.0 - tip_factor * 0.4
            v.co.x = center_local.x + offset.x * taper
            v.co.y = center_local.y + offset.y * taper

        # 3. Add slight twist along length
        twist_amount = math.radians(15 + random.random() * 20) * (1 if idx % 2 == 0 else -1)
        twist_angle = t * twist_amount
        rx = v.co.x - center_local.x
        ry = v.co.y - center_local.y
        cos_a = math.cos(twist_angle)
        sin_a = math.sin(twist_angle)
        v.co.x = center_local.x + rx * cos_a - ry * sin_a
        v.co.y = center_local.y + rx * sin_a + ry * cos_a

        # 4. Add slight curve/bend
        bend_dir = Vector((
            0.1 * math.sin(idx * 1.3),
            0.08 * math.cos(idx * 0.9),
            0
        ))
        v.co += bend_dir * t * t * 0.15

        # 5. Add subtle organic noise
        noise = (random.random() - 0.5) * 0.008 * (1 - t * 0.5)
        if v.normal.length > 0.001:
            v.co += v.normal * noise

    bm.to_mesh(me)
    bm.free()
    me.update()

    # 6. Vary direction slightly - rotate each lock a bit differently
    rot_variation = math.radians(random.uniform(-8, 8))
    lock.rotation_euler.x += rot_variation
    lock.rotation_euler.y += math.radians(random.uniform(-6, 6))

    # 7. Vary length slightly
    length_var = 1.0 + random.uniform(-0.08, 0.12)
    lock.scale.z *= length_var

    print(f"  Refined: {lock.name}")

print(f"  Refined {len(crest_locks)} crest locks")


# ================================================================
# PHASE 3 — TAIL PLUME REFINEMENT (Target 4)
# ================================================================
print("\n=== PHASE 3: Tail Plume Refinement ===")

# Main tail body
tail_main = get_obj("KIKO | dominant curved plume tail")
if tail_main:
    # Increase overall volume slightly
    scale_object_from_center(tail_main, (1.12, 1.15, 1.05))
    displace_verts_outward(tail_main, 0.015)
    print("  Expanded main tail volume")

# Tail plume locks
tail_locks = []
for i in range(1, 14):
    name = f"KIKO | tail plume lock {i:02d}"
    obj = get_obj(name)
    if obj:
        tail_locks.append((i, obj))

for idx, (num, lock) in enumerate(tail_locks):
    me = lock.data
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
    center_local = sum(local_verts, Vector((0,0,0))) / len(local_verts)

    random.seed(num * 13 + 7)

    for v in bm.verts:
        t = (v.co.z - min_z) / max(z_range, 0.001)

        # Increase lateral volume
        offset = v.co - center_local
        lateral_expand = 1.15 + random.uniform(0, 0.15)
        v.co.x = center_local.x + offset.x * lateral_expand
        v.co.y = center_local.y + offset.y * lateral_expand

        # Taper tips
        if t > 0.6:
            tip_t = (t - 0.6) / 0.4
            taper = 1.0 - tip_t * 0.3
            v.co.x = center_local.x + (v.co.x - center_local.x) * taper
            v.co.y = center_local.y + (v.co.y - center_local.y) * taper

        # Slight organic waviness
        wave = math.sin(t * math.pi * 2 + num * 0.8) * 0.008
        if v.normal.length > 0.001:
            v.co += v.normal * wave

    bm.to_mesh(me)
    bm.free()
    me.update()

    # Stagger lengths
    length_var = 1.0 + random.uniform(-0.1, 0.15)
    lock.scale.z *= length_var

    # Vary direction slightly
    lock.rotation_euler.x += math.radians(random.uniform(-10, 10))
    lock.rotation_euler.y += math.radians(random.uniform(-8, 8))

    print(f"  Refined: {lock.name}")

# Add extra wispy locks at tail edges for silhouette breakup
tail_center = get_mesh_center(tail_main) if tail_main else center
tail_extras = 0
for i in range(6):
    random.seed(i * 17 + 33)
    angle = math.radians(i * 60 + random.uniform(-15, 15))
    r = 0.25 + random.uniform(0, 0.1)
    pos = (
        tail_center.x + r * math.cos(angle),
        tail_center.y + r * math.sin(angle),
        tail_center.z + random.uniform(-0.2, 0.2)
    )
    mat_choices = ["Fur | deep teal blue-gray", "Fur | warm integrated cream", "Fur | burnt apricot"]
    mat_name = mat_choices[i % 3]
    mass = create_fur_mass(
        f"KIKO | tail wisp {i+1:02d}",
        pos,
        scale=(0.06, 0.04, 0.15 + random.uniform(0, 0.08)),
        direction=(
            math.cos(angle) * 0.5,
            math.sin(angle) * 0.5,
            0.7 + random.uniform(-0.2, 0.2)
        ),
        material_name=mat_name,
        subdivisions=1,
        noise_strength=0.008
    )
    tail_extras += 1

print(f"  Added {tail_extras} tail edge wisps")


# ================================================================
# PHASE 4 — FUR SILHOUETTE BREAKUP (Target 5)
# ================================================================
print("\n=== PHASE 4: Fur Silhouette Breakup ===")

fur_masses_added = 0

# Body mesh reference
body_center_z = all_min.z + height * 0.45  # torso center

# --- Jaw / chin tufts ---
jaw_z = all_min.z + height * 0.68
for side, sign in [("L", 1), ("R", -1), ("C", 0)]:
    x_off = sign * 0.18
    pos = (center.x + x_off, center.y - 0.22, jaw_z)
    create_fur_mass(
        f"KIKO | jaw tuft {side}",
        pos,
        scale=(0.08, 0.06, 0.10),
        direction=(sign * 0.2, -0.7, -0.5),
        material_name="Fur | warm integrated cream",
        subdivisions=1,
        noise_strength=0.008
    )
    fur_masses_added += 1

# --- Neck ruff ---
neck_z = all_min.z + height * 0.60
for i in range(4):
    angle = math.radians(-60 + i * 40)
    r = 0.32
    pos = (
        center.x + r * math.sin(angle),
        center.y - r * math.cos(angle),
        neck_z + random.uniform(-0.05, 0.05)
    )
    create_fur_mass(
        f"KIKO | neck ruff {i+1}",
        pos,
        scale=(0.10, 0.07, 0.12),
        direction=(math.sin(angle), -math.cos(angle), -0.4),
        material_name="Fur | warm integrated cream",
        subdivisions=1,
        noise_strength=0.01
    )
    fur_masses_added += 1

# --- Chest ruff (below scarf) ---
chest_z = all_min.z + height * 0.48
for i in range(3):
    x_off = (i - 1) * 0.15
    pos = (center.x + x_off, center.y - 0.28, chest_z)
    create_fur_mass(
        f"KIKO | chest ruff {i+1}",
        pos,
        scale=(0.10, 0.06, 0.09),
        direction=(x_off * 0.5, -0.6, -0.5),
        material_name="Fur | warm integrated cream",
        subdivisions=1,
        noise_strength=0.008
    )
    fur_masses_added += 1

# --- Shoulder tufts ---
shoulder_z = all_min.z + height * 0.52
for side, sign in [("L", 1), ("R", -1)]:
    pos = (center.x + sign * 0.45, center.y - 0.05, shoulder_z)
    create_fur_mass(
        f"KIKO | shoulder tuft {side}",
        pos,
        scale=(0.12, 0.08, 0.10),
        direction=(sign * 0.7, -0.3, 0.2),
        material_name="Fur | deep teal blue-gray",
        subdivisions=1,
        noise_strength=0.01
    )
    fur_masses_added += 1

# --- Forearm fur ---
forearm_z = all_min.z + height * 0.35
for side, sign in [("L", 1), ("R", -1)]:
    for j in range(2):
        angle = math.radians(-30 + j * 60)
        pos = (
            center.x + sign * 0.55,
            center.y + 0.1 * math.sin(angle),
            forearm_z + j * 0.08
        )
        create_fur_mass(
            f"KIKO | forearm fur {side} {j+1}",
            pos,
            scale=(0.07, 0.05, 0.09),
            direction=(sign * 0.5, math.sin(angle) * 0.3, -0.4),
            material_name="Fur | soft teal highlights",
            subdivisions=1,
            noise_strength=0.006
        )
        fur_masses_added += 1

# --- Thigh tufts ---
thigh_z = all_min.z + height * 0.25
for side, sign in [("L", 1), ("R", -1)]:
    pos = (center.x + sign * 0.32, center.y - 0.05, thigh_z)
    create_fur_mass(
        f"KIKO | thigh tuft {side}",
        pos,
        scale=(0.10, 0.07, 0.10),
        direction=(sign * 0.5, -0.3, -0.5),
        material_name="Fur | deep teal blue-gray",
        subdivisions=1,
        noise_strength=0.008
    )
    fur_masses_added += 1

# --- Ankle tufts ---
ankle_z = all_min.z + height * 0.10
for side, sign in [("L", 1), ("R", -1)]:
    for j in range(2):
        a = math.radians(-45 + j * 90)
        pos = (
            center.x + sign * 0.28 + 0.05 * math.sin(a),
            center.y + 0.08 * math.cos(a),
            ankle_z
        )
        create_fur_mass(
            f"KIKO | ankle tuft {side} {j+1}",
            pos,
            scale=(0.06, 0.05, 0.08),
            direction=(math.sin(a) * 0.3, math.cos(a) * 0.3, -0.6),
            material_name="Fur | soft teal highlights",
            subdivisions=1,
            noise_strength=0.005
        )
        fur_masses_added += 1

print(f"  Added {fur_masses_added} fur silhouette masses")

# Also roughen the main body mesh slightly for organic feel
if body:
    me = body.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.normal_update()

    random.seed(99)
    for v in bm.verts:
        # Very subtle surface noise to break up smooth read
        noise = (random.random() - 0.5) * 0.006
        if v.normal.length > 0.001:
            v.co += v.normal * noise

    bm.to_mesh(me)
    bm.free()
    me.update()
    print("  Added subtle body surface noise")


# ================================================================
# PHASE 5 — MATERIAL FIXES (Target 6)
# ================================================================
print("\n=== PHASE 5: Material Fixes ===")

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

mat_fixed = 0
for mat in bpy.data.materials:
    if mat.name in MATERIAL_COLORS and mat.use_nodes:
        base, rough, metal, spec = MATERIAL_COLORS[mat.name]
        for node in mat.node_tree.nodes:
            if node.type == 'BSDF_PRINCIPLED':
                node.inputs['Base Color'].default_value = base
                node.inputs['Roughness'].default_value = rough
                node.inputs['Metallic'].default_value = metal
                # Set specular/IOR for low specular on fur
                try:
                    node.inputs['Specular IOR Level'].default_value = spec
                except:
                    try:
                        node.inputs['Specular'].default_value = spec
                    except:
                        pass
                mat_fixed += 1

# Add emission to catchlights
for mat in bpy.data.materials:
    if mat.name == "Eye | soft catchlight":
        for node in mat.node_tree.nodes:
            if node.type == 'BSDF_PRINCIPLED':
                try:
                    node.inputs['Emission Color'].default_value = (1, 1, 1, 1)
                    node.inputs['Emission Strength'].default_value = 0.5
                except:
                    pass

print(f"  Fixed {mat_fixed} materials")


# ================================================================
# PHASE 6 — SAVE AND EXPORT
# ================================================================
print("\n=== PHASE 6: Save and Export ===")

# Save .blend
os.makedirs(os.path.dirname(BLEND_V3), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=BLEND_V3)
print(f"  Saved: {BLEND_V3}")

# Export GLB with materials
# Select all mesh objects
bpy.ops.object.select_all(action='SELECT')

os.makedirs(os.path.dirname(GLB_V3), exist_ok=True)
bpy.ops.export_scene.gltf(
    filepath=GLB_V3,
    export_format='GLB',
    use_selection=False,
    export_apply=True,
    export_materials='EXPORT',
    export_colors=True,
    export_normals=True,
)
print(f"  Exported: {GLB_V3}")

# Count final stats
final_objects = len([o for o in bpy.data.objects if o.type == 'MESH'])
final_verts = sum(len(o.data.vertices) for o in bpy.data.objects if o.type == 'MESH')
final_faces = sum(len(o.data.polygons) for o in bpy.data.objects if o.type == 'MESH')
final_mats = len(bpy.data.materials)

print(f"\n=== V3 STATS ===")
print(f"Mesh objects: {final_objects}")
print(f"Vertices: {final_verts}")
print(f"Faces: {final_faces}")
print(f"Materials: {final_mats}")

# ================================================================
# PHASE 7 — VERIFY GLB ROUNDTRIP
# ================================================================
print("\n=== PHASE 7: GLB Roundtrip Verification ===")

# Re-import into clean scene
bpy.ops.wm.read_homefile(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB_V3)

# Check materials
mat_check = {}
for mat in bpy.data.materials:
    if mat.use_nodes:
        for node in mat.node_tree.nodes:
            if node.type == 'BSDF_PRINCIPLED':
                bc = node.inputs['Base Color'].default_value
                is_white = (bc[0] > 0.98 and bc[1] > 0.98 and bc[2] > 0.98)
                mat_check[mat.name] = {
                    "base_color": [round(bc[0], 3), round(bc[1], 3), round(bc[2], 3)],
                    "is_white": is_white,
                    "roughness": round(node.inputs['Roughness'].default_value, 3),
                }

white_count = sum(1 for v in mat_check.values() if v["is_white"])
total_mats = len(mat_check)

print(f"Materials checked: {total_mats}")
print(f"Materials still white after roundtrip: {white_count}")
for name, info in sorted(mat_check.items()):
    status = "WHITE!" if info["is_white"] else "OK"
    print(f"  {status} {name}: BaseColor={info['base_color']}, Rough={info['roughness']}")

# Save roundtrip verification
roundtrip_path = os.path.join(PROJECT, "projects/characters/kiko/reports/v3_glb_roundtrip.json")
os.makedirs(os.path.dirname(roundtrip_path), exist_ok=True)
with open(roundtrip_path, 'w') as f:
    json.dump({
        "glb": GLB_V3,
        "total_materials": total_mats,
        "white_materials": white_count,
        "materials": mat_check,
        "pass": white_count == 0
    }, f, indent=2)

print(f"\n  Roundtrip report: {roundtrip_path}")
print(f"  Material export {'PASS' if white_count == 0 else 'FAIL'}")
print("\n=== STAGE 5.1 REFINEMENT COMPLETE ===")
