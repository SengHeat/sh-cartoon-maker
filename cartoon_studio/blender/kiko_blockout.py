#!/usr/bin/env python3
"""KIKO blockout — proportion-matched proxy mesh + base armature.

Run standalone:
    blender -b -P cartoon_studio/blender/kiko_blockout.py

Generates KIKO_blockout_v001.blend in the working directory with:
  - Proxy geometry built to the character bible's head-unit proportions
  - Full deform skeleton with ear, tail, and finger chains
  - Material IDs for the four fur regions + skin/detail colours
  - Named per the bible's KIKO_ + GEO_/RIG_/MAT_ convention

All measurements derive from one constant (HU) so the blockout scales
uniformly if you change it.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


# ---------------------------------------------------------------------------
# Head-unit scale — 1 HU = chin-to-crown, crest excluded.
# Everything below is expressed as multiples of HU.
# ---------------------------------------------------------------------------
HU = 0.75  # Blender-units per head-unit


# ---------------------------------------------------------------------------
# Bible proportion table (in head-units)
# ---------------------------------------------------------------------------
TOTAL_HEIGHT    = 3.25   # standing, crest excluded
CREST_HEIGHT    = 0.55   # above crown
EYE_SPAN_RATIO = 0.45   # fraction of face width
EAR_HEIGHT      = 0.90
TORSO_HEIGHT    = 1.10
ARM_LENGTH      = 1.30
HAND_SIZE       = 0.45
LEG_LENGTH      = 1.10
FOOT_LENGTH     = 0.60
TAIL_LENGTH     = 1.10   # body-lengths (≈ TOTAL_HEIGHT)

# Derived absolute sizes (Blender units)
HEAD_R     = HU * 0.50            # head sphere radius
TORSO_H    = HU * TORSO_HEIGHT
LEG_H      = HU * LEG_LENGTH
ARM_H      = HU * ARM_LENGTH
HAND_R     = HU * HAND_SIZE * 0.5
FOOT_L     = HU * FOOT_LENGTH
EAR_H      = HU * EAR_HEIGHT
CREST_H    = HU * CREST_HEIGHT

# Vertical layout — ground at z = 0
FOOT_Z     = 0.0
ANKLE_Z    = FOOT_Z + 0.08 * HU
KNEE_Z     = FOOT_Z + LEG_H * 0.48
HIP_Z      = FOOT_Z + LEG_H
SPINE_Z    = HIP_Z + TORSO_H * 0.40
CHEST_Z    = HIP_Z + TORSO_H * 0.82
NECK_Z     = HIP_Z + TORSO_H
HEAD_Z     = NECK_Z + HU * 0.30
CROWN_Z    = HEAD_Z + HU
CREST_TOP  = CROWN_Z + CREST_H

SHOULDER_Z = CHEST_Z - 0.05 * HU
ELBOW_Z    = SHOULDER_Z - ARM_H * 0.42
WRIST_Z    = SHOULDER_Z - ARM_H * 0.82
HAND_Z     = SHOULDER_Z - ARM_H

SHOULDER_X = 0.30 * HU  # half-shoulder width

TAIL_BASE_Z = HIP_Z - 0.05 * HU


# ---------------------------------------------------------------------------
# Bible colour palette (hex approximations → linear-ish RGBA)
# ---------------------------------------------------------------------------
def _hex(h: str) -> tuple[float, float, float, float]:
    """Convert '#RRGGBB' to a linear-float RGBA tuple (alpha = 1)."""
    r, g, b = int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)
    # sRGB → linear approximation (gamma 2.2)
    return (
        (r / 255) ** 2.2,
        (g / 255) ** 2.2,
        (b / 255) ** 2.2,
        1.0,
    )


PALETTE = {
    "MAT_fur_base":  _hex("#6F8C88"),   # desaturated teal / blue-grey
    "MAT_fur_cream": _hex("#ECE1CE"),   # warm cream / off-white
    "MAT_fur_rust":  _hex("#C76B38"),   # rust / burnt orange
    "MAT_fur_crest": _hex("#B8A066"),   # teal-base, blonde/tan streaks
    "MAT_skin_nose": _hex("#E3A0A0"),   # dusty pink
    "MAT_iris":      _hex("#A5571F"),   # amber / orange-brown
    "MAT_ear_skin":  _hex("#C98E73"),   # muted pink-tan
    "MAT_paw_pad":   _hex("#7E99A0"),   # blue-grey paw pad
    "MAT_freckle":   _hex("#8A4A2A"),   # deep rust-brown
    "MAT_costume":   _hex("#5A3A22"),   # leather brown (gear placeholder)
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _mat(name: str, color: tuple[float, float, float, float]) -> bpy.types.Material:
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.diffuse_color = color
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = color
    return mat


def _sphere(name: str, location: Vector, radius: float, mat: bpy.types.Material) -> bpy.types.Object:
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=10, radius=radius, location=location)
    obj = bpy.context.object
    obj.name = name
    for p in obj.data.polygons:
        p.use_smooth = True
    obj.data.materials.append(mat)
    return obj


def _cube(name: str, location: Vector, scale: tuple[float, float, float], mat: bpy.types.Material) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(size=1, location=location, scale=scale)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    return obj


def _cylinder(name: str, a: Vector, b: Vector, radius: float, mat: bpy.types.Material) -> bpy.types.Object:
    delta = b - a
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=12, radius=radius, depth=delta.length,
        location=(a + b) / 2,
    )
    obj = bpy.context.object
    obj.name = name
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = delta.to_track_quat("Z", "Y")
    for p in obj.data.polygons:
        p.use_smooth = True
    obj.data.materials.append(mat)
    return obj


def _cone(name: str, location: Vector, radius: float, depth: float,
          mat: bpy.types.Material, rotation: tuple[float, float, float] = (0, 0, 0)) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cone_add(
        vertices=12, radius1=radius, radius2=0, depth=depth,
        location=location, rotation=rotation,
    )
    obj = bpy.context.object
    obj.name = name
    for p in obj.data.polygons:
        p.use_smooth = True
    obj.data.materials.append(mat)
    return obj


# ---------------------------------------------------------------------------
# Build materials
# ---------------------------------------------------------------------------
def build_materials() -> dict[str, bpy.types.Material]:
    return {name: _mat(name, color) for name, color in PALETTE.items()}


# ---------------------------------------------------------------------------
# Build proxy geometry
# ---------------------------------------------------------------------------
def build_proxy(mats: dict[str, bpy.types.Material]) -> dict[str, bpy.types.Object]:
    """Create named proxy primitives for every body region and costume piece."""
    base = mats["MAT_fur_base"]
    cream = mats["MAT_fur_cream"]
    rust = mats["MAT_fur_rust"]
    crest_mat = mats["MAT_fur_crest"]
    nose_mat = mats["MAT_skin_nose"]
    iris_mat = mats["MAT_iris"]
    ear_mat = mats["MAT_ear_skin"]
    costume = mats["MAT_costume"]
    freckle = mats["MAT_freckle"]

    geo: dict[str, bpy.types.Object] = {}

    # --- Head ---
    geo["KIKO_GEO_head"] = _sphere(
        "KIKO_GEO_head", Vector((0, 0, HEAD_Z + HEAD_R)), HEAD_R, base,
    )
    # Muzzle bump (cream underside)
    geo["KIKO_GEO_muzzle"] = _sphere(
        "KIKO_GEO_muzzle",
        Vector((0, -HEAD_R * 0.72, HEAD_Z + HEAD_R * 0.55)),
        HEAD_R * 0.42, cream,
    )
    # Nose
    geo["KIKO_GEO_nose"] = _sphere(
        "KIKO_GEO_nose",
        Vector((0, -HEAD_R * 0.95, HEAD_Z + HEAD_R * 0.65)),
        HEAD_R * 0.12, nose_mat,
    )
    # Cheek ruffs (cream)
    for sign, side in ((1, "L"), (-1, "R")):
        geo[f"KIKO_GEO_cheek_ruff_{side}"] = _sphere(
            f"KIKO_GEO_cheek_ruff_{side}",
            Vector((sign * HEAD_R * 0.55, -HEAD_R * 0.35, HEAD_Z + HEAD_R * 0.40)),
            HEAD_R * 0.28, cream,
        )

    # --- Eyes ---
    eye_half_span = HEAD_R * EYE_SPAN_RATIO
    for sign, side in ((1, "L"), (-1, "R")):
        cx = sign * eye_half_span * 0.55
        cz = HEAD_Z + HEAD_R * 0.85
        geo[f"KIKO_GEO_eye_{side}"] = _sphere(
            f"KIKO_GEO_eye_{side}",
            Vector((cx, -HEAD_R * 0.82, cz)),
            HEAD_R * 0.22, cream,
        )
        geo[f"KIKO_GEO_iris_{side}"] = _sphere(
            f"KIKO_GEO_iris_{side}",
            Vector((cx, -HEAD_R * 0.96, cz)),
            HEAD_R * 0.11, iris_mat,
        )

    # --- Ears ---
    for sign, side in ((1, "L"), (-1, "R")):
        ear_base_z = CROWN_Z - 0.05 * HU
        ear_tip_z = ear_base_z + EAR_H
        ear_x = sign * HEAD_R * 0.72
        geo[f"KIKO_GEO_ear_{side}"] = _cone(
            f"KIKO_GEO_ear_{side}",
            Vector((ear_x, 0, (ear_base_z + ear_tip_z) / 2)),
            HEAD_R * 0.38, EAR_H, base,
            rotation=(0, 0, sign * math.radians(12)),
        )
        # Inner ear surface (rust)
        geo[f"KIKO_GEO_ear_inner_{side}"] = _cone(
            f"KIKO_GEO_ear_inner_{side}",
            Vector((ear_x * 1.02, -0.01, (ear_base_z + ear_tip_z) / 2 + 0.01)),
            HEAD_R * 0.26, EAR_H * 0.85, ear_mat,
            rotation=(0, 0, sign * math.radians(12)),
        )
        # Ear freckle spots
        for i in range(3):
            geo[f"KIKO_GEO_ear_spot_{i}_{side}"] = _sphere(
                f"KIKO_GEO_ear_spot_{i}_{side}",
                Vector((ear_x * 1.04, -0.03, ear_base_z + EAR_H * (0.3 + i * 0.2))),
                HEAD_R * 0.04, freckle,
            )

    # --- Crest (mohawk tuft) ---
    for i, frac in enumerate((-0.4, -0.2, 0.0, 0.2, 0.4)):
        spike_h = CREST_H * (1.0 if frac == 0 else 0.72)
        spike_x = frac * HEAD_R * 0.6
        spike_z = CROWN_Z + spike_h * 0.5
        geo[f"KIKO_GEO_crest_{i}"] = _cone(
            f"KIKO_GEO_crest_{i}",
            Vector((spike_x, 0.02, spike_z)),
            HEAD_R * 0.14, spike_h, crest_mat,
            rotation=(math.radians(-12), 0, math.radians(-frac * 55)),
        )

    # --- Torso ---
    torso_cy = (HIP_Z + NECK_Z) / 2
    geo["KIKO_GEO_torso"] = _cube(
        "KIKO_GEO_torso",
        Vector((0, 0, torso_cy)),
        (HU * 0.52, HU * 0.38, TORSO_H * 0.5),
        base,
    )
    # Belly / chest (cream underside)
    geo["KIKO_GEO_belly"] = _cube(
        "KIKO_GEO_belly",
        Vector((0, -HU * 0.12, torso_cy - TORSO_H * 0.08)),
        (HU * 0.38, HU * 0.18, TORSO_H * 0.42),
        cream,
    )
    # Neck
    geo["KIKO_GEO_neck"] = _cylinder(
        "KIKO_GEO_neck",
        Vector((0, 0, NECK_Z)), Vector((0, 0, HEAD_Z)),
        HU * 0.15, base,
    )

    # --- Arms ---
    for sign, side in ((1, "L"), (-1, "R")):
        sx = sign * SHOULDER_X
        upper_a = Vector((sx, 0, SHOULDER_Z))
        upper_b = Vector((sign * (SHOULDER_X + ARM_H * 0.36), 0, ELBOW_Z))
        geo[f"KIKO_GEO_upper_arm_{side}"] = _cylinder(
            f"KIKO_GEO_upper_arm_{side}", upper_a, upper_b, HU * 0.10, base,
        )
        lower_a = upper_b
        lower_b = Vector((sign * (SHOULDER_X + ARM_H * 0.58), 0, WRIST_Z))
        geo[f"KIKO_GEO_forearm_{side}"] = _cylinder(
            f"KIKO_GEO_forearm_{side}", lower_a, lower_b, HU * 0.08, base,
        )
        # Hand (oversized)
        geo[f"KIKO_GEO_hand_{side}"] = _sphere(
            f"KIKO_GEO_hand_{side}",
            Vector((sign * (SHOULDER_X + ARM_H * 0.65), 0, HAND_Z)),
            HAND_R, cream,
        )
        # Finger stubs (4 chunky digits per bible)
        for fi in range(4):
            angle = math.radians(-30 + fi * 20)
            dx = sign * math.cos(angle) * HAND_R * 0.9
            dz = math.sin(angle) * HAND_R * 0.9
            tip = Vector((
                sign * (SHOULDER_X + ARM_H * 0.65) + dx,
                0,
                HAND_Z + dz,
            ))
            geo[f"KIKO_GEO_finger_{fi}_{side}"] = _cylinder(
                f"KIKO_GEO_finger_{fi}_{side}",
                Vector((sign * (SHOULDER_X + ARM_H * 0.65), 0, HAND_Z)),
                tip, HU * 0.035, base,
            )

    # --- Legs ---
    for sign, side in ((1, "L"), (-1, "R")):
        hx = sign * HU * 0.18
        thigh_a = Vector((hx, 0, HIP_Z))
        thigh_b = Vector((hx, 0, KNEE_Z))
        geo[f"KIKO_GEO_thigh_{side}"] = _cylinder(
            f"KIKO_GEO_thigh_{side}", thigh_a, thigh_b, HU * 0.13, base,
        )
        shin_a = thigh_b
        shin_b = Vector((hx, 0, ANKLE_Z))
        geo[f"KIKO_GEO_shin_{side}"] = _cylinder(
            f"KIKO_GEO_shin_{side}", shin_a, shin_b, HU * 0.10, base,
        )
        # Foot (big, plantigrade)
        geo[f"KIKO_GEO_foot_{side}"] = _cube(
            f"KIKO_GEO_foot_{side}",
            Vector((hx, -FOOT_L * 0.25, FOOT_Z + HU * 0.06)),
            (HU * 0.16, FOOT_L * 0.5, HU * 0.08),
            base,
        )
        # Toe stubs (3-4 toes)
        for ti in range(3):
            tx = hx + (ti - 1) * HU * 0.06
            geo[f"KIKO_GEO_toe_{ti}_{side}"] = _sphere(
                f"KIKO_GEO_toe_{ti}_{side}",
                Vector((tx, -FOOT_L * 0.7, FOOT_Z + HU * 0.03)),
                HU * 0.04, base,
            )

    # --- Tail ---
    # Thick plume, curving up and back, ~1.1 body-lengths.
    tail_total = HU * TAIL_LENGTH * TOTAL_HEIGHT
    segments = 6
    seg_len = tail_total / segments
    prev = Vector((0, HU * 0.15, TAIL_BASE_Z))
    for i in range(segments):
        t = (i + 1) / segments
        # Arc upward and back
        nxt = Vector((
            0,
            HU * 0.15 + t * tail_total * 0.38,
            TAIL_BASE_Z + math.sin(t * math.pi * 0.65) * tail_total * 0.35,
        ))
        # Taper radius from thick base to thinner tip
        radius = HU * 0.14 * (1.0 - t * 0.45)
        # Material: teal → cream → rust banding
        if t < 0.4:
            mat = base
        elif t < 0.7:
            mat = cream
        else:
            mat = rust
        geo[f"KIKO_GEO_tail_{i + 1:02d}"] = _cylinder(
            f"KIKO_GEO_tail_{i + 1:02d}", prev, nxt, radius, mat,
        )
        prev = nxt

    # --- Costume placeholders ---
    # Scarf / cowl (neck area)
    geo["KIKO_GEO_scarf"] = _cube(
        "KIKO_GEO_scarf",
        Vector((0, 0, NECK_Z + HU * 0.05)),
        (HU * 0.30, HU * 0.30, HU * 0.10),
        rust,
    )
    # Vest (torso)
    geo["KIKO_GEO_vest"] = _cube(
        "KIKO_GEO_vest",
        Vector((0, -HU * 0.08, CHEST_Z - TORSO_H * 0.18)),
        (HU * 0.42, HU * 0.06, TORSO_H * 0.32),
        base,
    )
    # Belt
    geo["KIKO_GEO_belt"] = _cube(
        "KIKO_GEO_belt",
        Vector((0, 0, HIP_Z + HU * 0.05)),
        (HU * 0.34, HU * 0.28, HU * 0.04),
        costume,
    )
    # Backpack
    geo["KIKO_GEO_backpack"] = _cube(
        "KIKO_GEO_backpack",
        Vector((0, HU * 0.28, CHEST_Z - TORSO_H * 0.10)),
        (HU * 0.22, HU * 0.14, TORSO_H * 0.25),
        costume,
    )
    # Harness straps (two diagonal capsules)
    for sign, side in ((1, "L"), (-1, "R")):
        geo[f"KIKO_GEO_strap_{side}"] = _cylinder(
            f"KIKO_GEO_strap_{side}",
            Vector((sign * HU * 0.18, -HU * 0.16, CHEST_Z)),
            Vector((sign * HU * 0.05, HU * 0.12, HIP_Z + HU * 0.10)),
            HU * 0.025, costume,
        )

    return geo


# ---------------------------------------------------------------------------
# Build armature
# ---------------------------------------------------------------------------
def build_armature() -> bpy.types.Object:
    """Create the full deform skeleton per the bible's rig spec."""
    data = bpy.data.armatures.new("KIKO_RIG_data")
    data.display_type = "OCTAHEDRAL"
    arm_obj = bpy.data.objects.new("KIKO_RIG_armature", data)
    bpy.context.collection.objects.link(arm_obj)
    bpy.context.view_layer.objects.active = arm_obj

    bpy.ops.object.mode_set(mode="EDIT")

    def bone(name: str, head: tuple, tail: tuple, parent_name: str | None = None,
             deform: bool = True) -> None:
        b = data.edit_bones.new(name)
        b.head = head
        b.tail = tail
        if parent_name:
            b.parent = data.edit_bones[parent_name]
        b.use_deform = deform

    hx = HU * 0.18  # hip half-width

    # --- Spine chain ---
    bone("root",        (0, 0, 0),              (0, 0, HIP_Z))
    bone("COG",         (0, 0, HIP_Z),          (0, 0, HIP_Z + 0.15 * HU),   "root")
    bone("pelvis",      (0, 0, HIP_Z),          (0, 0, SPINE_Z),              "COG")
    bone("spine_01",    (0, 0, SPINE_Z),         (0, 0, CHEST_Z - TORSO_H * 0.15), "pelvis")
    bone("spine_02",    (0, 0, CHEST_Z - TORSO_H * 0.15), (0, 0, CHEST_Z),  "spine_01")
    bone("chest",       (0, 0, CHEST_Z),         (0, 0, NECK_Z),              "spine_02")
    bone("neck",        (0, 0, NECK_Z),          (0, 0, HEAD_Z),              "chest")
    bone("head",        (0, 0, HEAD_Z),          (0, 0, CROWN_Z),             "neck")
    bone("jaw",         (0, -HEAD_R * 0.4, HEAD_Z + HEAD_R * 0.3),
                        (0, -HEAD_R * 0.7, HEAD_Z + HEAD_R * 0.05), "head")

    # --- Ears (3 segments each) ---
    for sign, side in ((1, "L"), (-1, "R")):
        ear_x = sign * HEAD_R * 0.72
        ear_base = CROWN_Z - 0.05 * HU
        seg = EAR_H / 3
        bone(f"ear_01_{side}", (ear_x, 0, ear_base),
             (ear_x, 0, ear_base + seg), "head")
        bone(f"ear_02_{side}", (ear_x, 0, ear_base + seg),
             (ear_x, 0, ear_base + 2 * seg), f"ear_01_{side}")
        bone(f"ear_03_{side}", (ear_x, 0, ear_base + 2 * seg),
             (ear_x, 0, ear_base + 3 * seg), f"ear_02_{side}")

    # --- Eyes ---
    for sign, side in ((1, "L"), (-1, "R")):
        cx = sign * HEAD_R * EYE_SPAN_RATIO * 0.55
        cz = HEAD_Z + HEAD_R * 0.85
        bone(f"eye_{side}", (cx, -HEAD_R * 0.8, cz),
             (cx, -HEAD_R * 1.0, cz), "head")

    # Eye aim target (non-deform)
    bone("eye_aim", (0, -HEAD_R * 2.5, HEAD_Z + HEAD_R * 0.85),
         (0, -HEAD_R * 3.0, HEAD_Z + HEAD_R * 0.85), None, deform=False)

    # --- Arms ---
    for sign, side in ((1, "L"), (-1, "R")):
        sx = sign * SHOULDER_X
        elbow_x = sign * (SHOULDER_X + ARM_H * 0.36)
        wrist_x = sign * (SHOULDER_X + ARM_H * 0.58)
        hand_x = sign * (SHOULDER_X + ARM_H * 0.65)

        bone(f"clavicle_{side}", (0, 0, SHOULDER_Z + 0.05 * HU),
             (sx, 0, SHOULDER_Z), "chest")
        bone(f"upperarm_{side}", (sx, 0, SHOULDER_Z),
             (elbow_x, 0, ELBOW_Z), f"clavicle_{side}")
        bone(f"lowerarm_{side}", (elbow_x, 0, ELBOW_Z),
             (wrist_x, 0, WRIST_Z), f"upperarm_{side}")
        bone(f"hand_{side}", (wrist_x, 0, WRIST_Z),
             (hand_x, 0, HAND_Z), f"lowerarm_{side}")

        # Fingers (1-2 bones per digit, 4 digits)
        for fi in range(4):
            angle = math.radians(-30 + fi * 20)
            tip_dx = sign * math.cos(angle) * HAND_R * 0.9
            tip_dz = math.sin(angle) * HAND_R * 0.9
            bone(f"finger_{fi:02d}_01_{side}",
                 (hand_x, 0, HAND_Z),
                 (hand_x + tip_dx * 0.55, 0, HAND_Z + tip_dz * 0.55),
                 f"hand_{side}")
            bone(f"finger_{fi:02d}_02_{side}",
                 (hand_x + tip_dx * 0.55, 0, HAND_Z + tip_dz * 0.55),
                 (hand_x + tip_dx, 0, HAND_Z + tip_dz),
                 f"finger_{fi:02d}_01_{side}")

    # --- Legs ---
    for sign, side in ((1, "L"), (-1, "R")):
        lx = sign * hx
        bone(f"thigh_{side}", (lx, 0, HIP_Z),
             (lx, 0, KNEE_Z), "pelvis")
        bone(f"shin_{side}", (lx, 0, KNEE_Z),
             (lx, 0, ANKLE_Z), f"thigh_{side}")
        bone(f"foot_{side}", (lx, 0, ANKLE_Z),
             (lx, -FOOT_L * 0.5, FOOT_Z), f"shin_{side}")
        bone(f"toe_{side}", (lx, -FOOT_L * 0.5, FOOT_Z),
             (lx, -FOOT_L * 0.8, FOOT_Z), f"foot_{side}")

    # --- Tail (6 segments off pelvis) ---
    tail_total = HU * TAIL_LENGTH * TOTAL_HEIGHT
    prev_name = "pelvis"
    prev_pos = (0, HU * 0.15, TAIL_BASE_Z)
    for i in range(6):
        t = (i + 1) / 6
        nxt = (
            0,
            HU * 0.15 + t * tail_total * 0.38,
            TAIL_BASE_Z + math.sin(t * math.pi * 0.65) * tail_total * 0.35,
        )
        bname = f"tail_{i + 1:02d}"
        bone(bname, prev_pos, nxt, prev_name)
        prev_name = bname
        prev_pos = nxt

    # --- Controls (non-deform) ---
    bone("CTRL_root",   (0, 0.25 * HU, 0),    (0, 0.25 * HU, HIP_Z * 0.5), None, False)
    bone("CTRL_COG",    (0, 0.25 * HU, HIP_Z), (0, 0.25 * HU, SPINE_Z),     "CTRL_root", False)
    bone("CTRL_head",   (0, 0.25 * HU, HEAD_Z),(0, 0.25 * HU, CROWN_Z),     "CTRL_COG", False)

    for sign, side in ((1, "L"), (-1, "R")):
        bone(f"IK_foot_{side}",
             (sign * hx, -0.15 * HU, FOOT_Z),
             (sign * hx, -0.15 * HU, FOOT_Z + 0.15 * HU), None, False)
        bone(f"POLE_knee_{side}",
             (sign * hx, -1.0 * HU, KNEE_Z),
             (sign * hx, -1.0 * HU, KNEE_Z + 0.15 * HU), None, False)

    bpy.ops.object.mode_set(mode="OBJECT")
    return arm_obj


# ---------------------------------------------------------------------------
# Parent geometry to armature
# ---------------------------------------------------------------------------
def parent_to_armature(geo: dict[str, bpy.types.Object], arm: bpy.types.Object) -> None:
    """Armature-parent all proxy objects (no weights — this is a blockout)."""
    for obj in geo.values():
        obj.parent = arm


# ---------------------------------------------------------------------------
# Add reference empties for silhouette check
# ---------------------------------------------------------------------------
def add_silhouette_guides(arm: bpy.types.Object) -> None:
    """Add circle empties at key proportions for turnaround verification."""
    guides = {
        "KIKO_REF_ground":   (0, 0, FOOT_Z),
        "KIKO_REF_hip":      (0, 0, HIP_Z),
        "KIKO_REF_chest":    (0, 0, CHEST_Z),
        "KIKO_REF_crown":    (0, 0, CROWN_Z),
        "KIKO_REF_crest_top": (0, 0, CREST_TOP),
    }
    for name, loc in guides.items():
        empty = bpy.data.objects.new(name, None)
        empty.empty_display_type = "CIRCLE"
        empty.empty_display_size = HU * 0.6
        empty.location = loc
        empty.parent = arm
        bpy.context.collection.objects.link(empty)


# ---------------------------------------------------------------------------
# Scene setup
# ---------------------------------------------------------------------------
def setup_scene() -> None:
    # Clean default objects
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    # Set units and frame range
    bpy.context.scene.unit_settings.system = "METRIC"
    bpy.context.scene.unit_settings.scale_length = 1.0
    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = 120


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    setup_scene()
    mats = build_materials()
    arm = build_armature()
    geo = build_proxy(mats)
    parent_to_armature(geo, arm)
    add_silhouette_guides(arm)

    # Select armature and frame it
    bpy.context.view_layer.objects.active = arm
    arm.select_set(True)

    # Store bible metadata on the armature for downstream scripts
    arm["kiko_bible"] = {
        "head_unit": HU,
        "total_height_hu": TOTAL_HEIGHT,
        "crest_height_hu": CREST_HEIGHT,
        "version": "v001",
    }

    out = Path.cwd() / "KIKO_blockout_v001.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(out))
    print(f"\n[KIKO Blockout] Saved → {out}")
    print(f"  Head-unit:       {HU:.3f} BU")
    print(f"  Total height:    {TOTAL_HEIGHT * HU:.3f} BU  ({TOTAL_HEIGHT} HU)")
    print(f"  Crest top:       {CREST_TOP:.3f} BU")
    print(f"  Proxy objects:   {len(geo)}")
    print(f"  Materials:       {len(mats)}")
    print(f"  Deform bones:    {sum(1 for b in arm.data.bones if b.use_deform)}")
    print(f"  Control bones:   {sum(1 for b in arm.data.bones if not b.use_deform)}")


if __name__ == "__main__":
    main()
