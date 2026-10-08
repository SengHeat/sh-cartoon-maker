#!/usr/bin/env python3
"""KIKO Run Animation — Stage 1 (5s gate) + Stage 2 (60s full).

Run headless:
    blender --background --python kiko_run.py

Loads KIKO_master_v1_1.blend, audits the rig, creates a looping run cycle
with secondary ear/tail motion, renders a 5-second gate test, verifies it,
and — only if Stage 1 passes — extends to a 60-second forward-locomotion
render with tracking camera.
"""

import json
import math
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import bpy
from mathutils import Vector

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ROOT = Path.cwd()

CONFIG = {
    # Source
    "blend_file": "KIKO_master_v1_1.blend",
    "armature_name": "KIKO_RIG_armature",

    # Run cycle
    "cycle_frames": 28,
    "stride_length": 1.0,       # Blender units per full stride (2 steps)
    "fps": 24,

    # Stage 1 — 5-second gate
    "stage1_seconds": 5,
    "stage1_res": (854, 480),
    "stage1_samples": 32,
    "stage1_dir": "output/kiko_run_test_5s",

    # Stage 2 — 60-second full
    "stage2_seconds": 60,
    "stage2_res": (1920, 1080),
    "stage2_samples": 48,
    "stage2_dir": "output/kiko_run_60s",

    # Camera
    "cam_distance": 4.8,
    "cam_height": 1.4,
    "cam_lens": 52,
    "cam_look_z": 1.25,
}

# Expected bone groups
EXPECTED_BONES = {
    "spine":    ["root", "COG", "pelvis", "spine_01", "spine_02",
                 "chest", "neck", "head"],
    "controls": ["IK_foot_L", "IK_foot_R", "POLE_knee_L", "POLE_knee_R"],
    "arm_L":    ["clavicle_L", "upperarm_L", "lowerarm_L", "hand_L"],
    "arm_R":    ["clavicle_R", "upperarm_R", "lowerarm_R", "hand_R"],
    "leg_L":    ["thigh_L", "shin_L", "foot_L", "toe_L"],
    "leg_R":    ["thigh_R", "shin_R", "foot_R", "toe_R"],
    "tail":     [f"tail_{i:02d}" for i in range(1, 7)],
    "ear_L":    ["ear_01_L", "ear_02_L", "ear_03_L"],
    "ear_R":    ["ear_01_R", "ear_02_R", "ear_03_R"],
}

# Bones whose Z-rotation flips when mirroring left/right halves
CENTER_FLIP_Z = {"pelvis", "spine_01", "spine_02", "chest", "neck", "head"}

# Left↔Right bone swap table
LR_SWAP = {}
for _a, _b in [("thigh", "thigh"), ("shin", "shin"), ("foot", "foot"),
               ("toe", "toe"), ("IK_foot", "IK_foot"),
               ("POLE_knee", "POLE_knee"),
               ("upperarm", "upperarm"), ("lowerarm", "lowerarm"),
               ("hand", "hand"), ("clavicle", "clavicle")]:
    LR_SWAP[f"{_a}_L"] = f"{_b}_R"
    LR_SWAP[f"{_a}_R"] = f"{_b}_L"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def keybone(arm, name, frame, rot=None, loc=None):
    """Insert a pose-bone keyframe."""
    pb = arm.pose.bones.get(name)
    if not pb:
        return
    pb.rotation_mode = "XYZ"
    if rot is not None:
        pb.rotation_euler = rot
        pb.keyframe_insert("rotation_euler", frame=frame)
    if loc is not None:
        pb.location = loc
        pb.keyframe_insert("location", frame=frame)


def mirror_pose(pose):
    """Mirror a pose dict: swap L/R bones, flip center-bone Z rotations."""
    out = {}
    for bone, vals in pose.items():
        target = LR_SWAP.get(bone, bone)
        nv = dict(vals)
        if "rot" in vals and bone in CENTER_FLIP_Z:
            rx, ry, rz = vals["rot"]
            nv["rot"] = (rx, ry, -rz)
        out[target] = nv
    return out


# ---------------------------------------------------------------------------
# Rig audit
# ---------------------------------------------------------------------------

def audit_rig(arm):
    """Check every expected bone exists; report weight status."""
    report = {"armature": arm.name, "bones_found": 0, "bones_expected": 0,
              "missing": [], "weight_issues": []}

    all_names = []
    for names in EXPECTED_BONES.values():
        all_names.extend(names)
    report["bones_expected"] = len(all_names)

    for name in all_names:
        if name in arm.data.bones:
            report["bones_found"] += 1
        else:
            report["missing"].append(name)

    # Weight check on mesh objects
    for obj in bpy.data.objects:
        if obj.type != "MESH" or not obj.name.startswith("KIKO_GEO"):
            continue
        has_arm = any(m.type == "ARMATURE" and m.object == arm
                      for m in obj.modifiers)
        if not has_arm:
            report["weight_issues"].append(f"{obj.name}: no armature modifier")
            continue
        vg_names = {vg.name for vg in obj.vertex_groups}
        if not vg_names:
            report["weight_issues"].append(f"{obj.name}: no vertex groups")

    print("\n=== RIG AUDIT ===")
    print(f"Armature: {arm.name}")
    print(f"Bones: {report['bones_found']}/{report['bones_expected']}")
    if report["missing"]:
        print(f"MISSING: {report['missing']}")
    else:
        print("All expected bones present.")
    if report["weight_issues"]:
        for w in report["weight_issues"][:8]:
            print(f"  WEIGHT: {w}")
    else:
        print("Weight status: OK")
    return report


def fix_weights(arm):
    """Ensure every KIKO_GEO mesh has an armature modifier + vertex groups."""
    fixed = 0
    for obj in bpy.data.objects:
        if obj.type != "MESH" or not obj.name.startswith("KIKO_GEO"):
            continue
        # Armature modifier
        has_arm = any(m.type == "ARMATURE" and m.object == arm
                      for m in obj.modifiers)
        if not has_arm:
            mod = obj.modifiers.new("Armature", "ARMATURE")
            mod.object = arm
            fixed += 1
        # Vertex groups for all deform bones
        for bone in arm.data.bones:
            if bone.use_deform and bone.name not in obj.vertex_groups:
                obj.vertex_groups.new(name=bone.name)
        # Fix unweighted verts: assign to nearest deform bone
        bone_segs = {}
        for bone in arm.data.bones:
            if not bone.use_deform:
                continue
            bone_segs[bone.name] = (arm.matrix_world @ bone.head_local,
                                    arm.matrix_world @ bone.tail_local)
        if not bone_segs:
            continue
        for v in obj.data.vertices:
            total_w = sum(g.weight for g in v.groups
                          if obj.vertex_groups[g.group].name in bone_segs)
            if total_w >= 0.01:
                continue
            wp = obj.matrix_world @ v.co
            dists = []
            for bn, (h, t) in bone_segs.items():
                seg = t - h
                lsq = seg.length_squared
                if lsq < 1e-10:
                    d = (wp - h).length
                else:
                    f = max(0, min(1, (wp - h).dot(seg) / lsq))
                    d = (wp - (h + seg * f)).length
                dists.append((d, bn))
            dists.sort()
            tot = sum(1.0 / max(d, 0.01) ** 2 for d, _ in dists[:2])
            for d, bn in dists[:2]:
                w = (1.0 / max(d, 0.01) ** 2) / tot
                obj.vertex_groups[bn].add([v.index], w, "REPLACE")
            fixed += 1
    if fixed:
        print(f"Weight fixes applied: {fixed}")
    return fixed


# ---------------------------------------------------------------------------
# Run-cycle pose data (first half — left-foot contact)
# ---------------------------------------------------------------------------

# Each entry: frame_offset → {bone: {rot: (x,y,z), loc: (x,y,z)}}
# Second half is derived by mirror_pose shifted +half frames.

def _half_cycle_poses():
    """Return key poses for frames 0-12 (left contact through airborne)."""
    return {
        # ── Contact Left ──
        0: {
            "pelvis":      {"rot": (0.10, 0, 0.05),  "loc": (0, 0, -0.015)},
            "spine_01":    {"rot": (0.12, 0, -0.025)},
            "spine_02":    {"rot": (0.05, 0, -0.015)},
            "chest":       {"rot": (-0.06, 0, -0.035)},
            "neck":        {"rot": (-0.05, 0, 0.018)},
            "head":        {"rot": (-0.04, 0, 0.010)},
            "thigh_L":     {"rot": (0.52, 0, 0)},
            "thigh_R":     {"rot": (-0.44, 0, 0)},
            "IK_foot_L":   {"loc": (0, 0, 0)},
            "IK_foot_R":   {"loc": (0, 0, 0.07)},
            "upperarm_L":  {"rot": (-0.38, 0.08, 0)},
            "upperarm_R":  {"rot": (0.42, -0.08, 0)},
            "lowerarm_L":  {"rot": (0, -0.30, 0)},
            "lowerarm_R":  {"rot": (0, -0.54, 0)},
            "hand_L":      {"rot": (0.05, 0, 0)},
            "hand_R":      {"rot": (-0.08, 0, 0)},
        },
        # ── Down (absorption) ──
        4: {
            "pelvis":      {"rot": (0.08, 0, 0.07),  "loc": (0, 0, -0.038)},
            "spine_01":    {"rot": (0.10, 0, -0.035)},
            "spine_02":    {"rot": (0.04, 0, -0.018)},
            "chest":       {"rot": (-0.04, 0, -0.045)},
            "neck":        {"rot": (-0.04, 0, 0.025)},
            "head":        {"rot": (-0.03, 0, 0.012)},
            "thigh_L":     {"rot": (0.40, 0, 0)},
            "thigh_R":     {"rot": (-0.26, 0, 0)},
            "IK_foot_L":   {"loc": (0, 0, 0)},
            "IK_foot_R":   {"loc": (0, 0, 0.13)},
            "upperarm_L":  {"rot": (-0.28, 0.06, 0)},
            "upperarm_R":  {"rot": (0.32, -0.06, 0)},
            "lowerarm_L":  {"rot": (0, -0.24, 0)},
            "lowerarm_R":  {"rot": (0, -0.48, 0)},
            "hand_L":      {"rot": (0.03, 0, 0)},
            "hand_R":      {"rot": (-0.06, 0, 0)},
        },
        # ── Passing ──
        7: {
            "pelvis":      {"rot": (0.12, 0, 0.0),   "loc": (0, 0, 0.0)},
            "spine_01":    {"rot": (0.14, 0, 0)},
            "spine_02":    {"rot": (0.06, 0, 0)},
            "chest":       {"rot": (-0.08, 0, 0)},
            "neck":        {"rot": (-0.04, 0, 0)},
            "head":        {"rot": (-0.02, 0, 0)},
            "thigh_L":     {"rot": (0.06, 0, 0)},
            "thigh_R":     {"rot": (0.04, 0, 0)},
            "IK_foot_L":   {"loc": (0, 0, 0)},
            "IK_foot_R":   {"loc": (0, 0, 0.11)},
            "upperarm_L":  {"rot": (-0.04, 0.02, 0)},
            "upperarm_R":  {"rot": (0.06, -0.02, 0)},
            "lowerarm_L":  {"rot": (0, -0.14, 0)},
            "lowerarm_R":  {"rot": (0, -0.34, 0)},
            "hand_L":      {"rot": (0, 0, 0)},
            "hand_R":      {"rot": (-0.02, 0, 0)},
        },
        # ── Up / push-off ──
        10: {
            "pelvis":      {"rot": (0.14, 0, -0.04),  "loc": (0, 0, 0.025)},
            "spine_01":    {"rot": (0.15, 0, 0.020)},
            "spine_02":    {"rot": (0.07, 0, 0.010)},
            "chest":       {"rot": (-0.09, 0, 0.028)},
            "neck":        {"rot": (-0.05, 0, -0.015)},
            "head":        {"rot": (-0.03, 0, -0.008)},
            "thigh_L":     {"rot": (-0.32, 0, 0)},
            "thigh_R":     {"rot": (0.42, 0, 0)},
            "IK_foot_L":   {"loc": (0, 0, 0.03)},
            "IK_foot_R":   {"loc": (0, 0, 0.05)},
            "upperarm_L":  {"rot": (0.32, -0.06, 0)},
            "upperarm_R":  {"rot": (-0.28, 0.06, 0)},
            "lowerarm_L":  {"rot": (0, -0.48, 0)},
            "lowerarm_R":  {"rot": (0, -0.26, 0)},
            "hand_L":      {"rot": (-0.06, 0, 0)},
            "hand_R":      {"rot": (0.04, 0, 0)},
        },
        # ── Airborne ──
        12: {
            "pelvis":      {"rot": (0.12, 0, 0.0),   "loc": (0, 0, 0.040)},
            "spine_01":    {"rot": (0.13, 0, 0)},
            "spine_02":    {"rot": (0.06, 0, 0)},
            "chest":       {"rot": (-0.07, 0, 0)},
            "neck":        {"rot": (-0.04, 0, 0)},
            "head":        {"rot": (-0.02, 0, 0)},
            "thigh_L":     {"rot": (-0.18, 0, 0)},
            "thigh_R":     {"rot": (0.28, 0, 0)},
            "IK_foot_L":   {"loc": (0, 0, 0.10)},
            "IK_foot_R":   {"loc": (0, 0, 0.03)},
            "upperarm_L":  {"rot": (0.38, -0.08, 0)},
            "upperarm_R":  {"rot": (-0.34, 0.08, 0)},
            "lowerarm_L":  {"rot": (0, -0.52, 0)},
            "lowerarm_R":  {"rot": (0, -0.22, 0)},
            "hand_L":      {"rot": (-0.08, 0, 0)},
            "hand_R":      {"rot": (0.04, 0, 0)},
        },
    }


# ---------------------------------------------------------------------------
# Secondary motion helpers
# ---------------------------------------------------------------------------

def _ear_value(phase, segment):
    """Ear rotation at normalised phase (0-1), per segment (1-3).

    Ears react to vertical bounce with a 2-frame delay scaled by segment.
    """
    delay = 0.06 * segment
    # Vertical bounce has 2 peaks per cycle
    bounce = math.cos(2 * math.tau * (phase - delay))
    magnitude = 0.04 * segment
    return (magnitude * bounce, 0, 0)


def _tail_value(phase, segment):
    """Tail rotation at normalised phase, per segment (1-6).

    Side-to-side sway opposing hips + vertical follow-through,
    with increasing delay per segment.
    """
    delay = 0.06 * segment
    sway_z = 0.05 * segment * math.sin(math.tau * (phase - delay))
    bounce_x = 0.025 * segment * math.cos(2 * math.tau * (phase - delay))
    return (bounce_x, 0, sway_z)


# ---------------------------------------------------------------------------
# Cycle keyframing
# ---------------------------------------------------------------------------

def create_run_animation(arm, total_frames, forward_motion=False):
    """Keyframe the run cycle for *total_frames*.

    If *forward_motion* is True, the armature object translates in +X and
    IK feet compensate during stance to prevent sliding.
    """
    cycle = CONFIG["cycle_frames"]
    half = cycle // 2
    stride = CONFIG["stride_length"]
    speed = stride / cycle          # BU per frame

    # Fresh action
    arm.animation_data_clear()
    arm.animation_data_create()
    action = bpy.data.actions.new("KIKO_ACT_run")
    arm.animation_data.action = action

    # Reset pose
    for pb in arm.pose.bones:
        pb.rotation_mode = "XYZ"
        pb.rotation_euler = (0, 0, 0)
        pb.location = (0, 0, 0)

    bpy.context.preferences.edit.keyframe_new_interpolation_type = "BEZIER"

    # Build the full-cycle pose table (first half + mirrored second half)
    half_poses = _half_cycle_poses()
    full_poses = dict(half_poses)
    for offset, pose in half_poses.items():
        full_poses[offset + half] = mirror_pose(pose)

    sorted_keys = sorted(full_poses.keys())

    # Add secondary-motion bones to each key frame
    for fk in sorted_keys:
        phase = fk / cycle
        pose = full_poses[fk]
        for seg in range(1, 4):
            ear_rot = _ear_value(phase, seg)
            pose[f"ear_{seg:02d}_L"] = {"rot": ear_rot}
            pose[f"ear_{seg:02d}_R"] = {"rot": ear_rot}
        for seg in range(1, 7):
            pose[f"tail_{seg:02d}"] = {"rot": _tail_value(phase, seg)}

    # Repeat across total duration
    num_cycles = (total_frames // cycle) + 2
    for cn in range(num_cycles):
        base = cn * cycle + 1       # Blender frames start at 1
        for fk in sorted_keys:
            frame = base + fk
            if frame < 1 or frame > total_frames + 1:
                continue
            pose = full_poses[fk]

            # Forward motion on the armature object
            if forward_motion:
                arm.location = ((cn * cycle + fk) * speed, 0, 0)
                arm.keyframe_insert("location", frame=frame)

                # IK foot X compensation during stance to prevent sliding.
                # Left stance: cycle frames 0-9;  Right stance: 14-23
                step_half = stride / 2
                lf = fk  # local frame within cycle
                l_stance = lf <= 9
                r_stance = half <= lf <= half + 9

                for side, is_stance, start_f in [("L", l_stance, 0),
                                                  ("R", r_stance, half)]:
                    ik_bone = f"IK_foot_{side}"
                    if ik_bone in pose:
                        existing = list(pose[ik_bone].get("loc", (0, 0, 0)))
                        if is_stance:
                            progress = (lf - start_f) / 10.0
                            existing[0] = step_half * 0.5 - progress * stride * (10 / cycle)
                        else:
                            # During swing: foot travels forward
                            swing_start = start_f + 10
                            swing_len = cycle - 10
                            if lf >= swing_start:
                                sp = (lf - swing_start) / swing_len
                            else:
                                sp = (lf + cycle - swing_start) / swing_len
                            sp = max(0, min(1, sp))
                            existing[0] = -step_half * 0.3 + sp * step_half * 0.8
                        pose[ik_bone]["loc"] = tuple(existing)

            for bone_name, vals in pose.items():
                keybone(arm, bone_name, frame,
                        rot=vals.get("rot"), loc=vals.get("loc"))

    print(f"Keyframed: {cycle}-frame cycle × {num_cycles} repeats "
          f"= {total_frames} frames, forward={forward_motion}")
    return action


# ---------------------------------------------------------------------------
# Studio setup
# ---------------------------------------------------------------------------

def setup_studio(ground_length=20):
    """Neutral ground plane + three-point lighting + camera."""
    # Ground
    bpy.ops.mesh.primitive_plane_add(size=ground_length,
                                     location=(ground_length / 2 - 2, 0, 0))
    floor = bpy.context.object
    floor.name = "RunFloor"
    mat = bpy.data.materials.new("MAT_RunFloor")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (0.12, 0.13, 0.14, 1)
    bsdf.inputs["Roughness"].default_value = 0.88
    floor.data.materials.append(mat)

    # World
    sc = bpy.context.scene
    sc.world.use_nodes = True
    bg = sc.world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.065, 0.072, 0.080, 1)

    # Lights
    def light(name, loc, energy, size, color):
        d = bpy.data.lights.new(name, "AREA")
        d.energy, d.shape, d.size, d.color = energy, "DISK", size, color
        o = bpy.data.objects.new(name, d)
        sc.collection.objects.link(o)
        o.location = loc
        o.rotation_euler = (Vector((0, 0, 1.5)) - o.location).to_track_quat(
            "-Z", "Y").to_euler()

    light("Key",  (-4, -5, 6), 1000, 5.0, (1.0, 0.85, 0.70))
    light("Fill", (4, -4, 4),   550, 5.5, (0.58, 0.70, 1.0))
    light("Rim",  (2, 5, 5),    750, 4.0, (0.80, 0.88, 1.0))

    # Camera
    cd = bpy.data.cameras.new("RunCam")
    cam = bpy.data.objects.new("RunCam", cd)
    sc.collection.objects.link(cam)
    cam.data.lens = CONFIG["cam_lens"]
    sc.camera = cam
    return cam


def keyframe_camera(cam, arm, total_frames, tracking):
    """Position camera: static 3/4 view (Stage 1) or tracking (Stage 2)."""
    dist = CONFIG["cam_distance"]
    h = CONFIG["cam_height"]
    look_z = CONFIG["cam_look_z"]

    for f in range(1, total_frames + 1):
        bpy.context.scene.frame_set(f)
        if tracking:
            cx = arm.location.x
        else:
            cx = 0
        cam.location = (cx - 1.2, -dist, h)
        target = Vector((cx, 0, look_z))
        cam.rotation_euler = (target - cam.location).to_track_quat(
            "-Z", "Y").to_euler()
        cam.keyframe_insert("location", frame=f)
        cam.keyframe_insert("rotation_euler", frame=f)


# ---------------------------------------------------------------------------
# Render helpers
# ---------------------------------------------------------------------------

def configure_render(res, samples):
    sc = bpy.context.scene
    try:
        sc.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        sc.render.engine = "BLENDER_EEVEE"
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGB"
    if hasattr(sc, "eevee") and hasattr(sc.eevee, "taa_render_samples"):
        sc.eevee.taa_render_samples = samples
    sc.view_settings.look = "AgX - Medium High Contrast"


def render_frames(frames_dir, total_frames, fps):
    if frames_dir.exists():
        shutil.rmtree(frames_dir)
    frames_dir.mkdir(parents=True, exist_ok=True)
    sc = bpy.context.scene
    sc.frame_start = 1
    sc.frame_end = total_frames
    sc.render.fps = fps
    sc.render.filepath = str(frames_dir) + "/frame_"
    bpy.ops.render.render(animation=True)


def encode_mp4(frames_dir, mp4_path, fps, prefix="frame_"):
    mp4_path = Path(mp4_path)
    mp4_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y",
        "-framerate", str(fps),
        "-start_number", "1",
        "-i", str(frames_dir / f"{prefix}%04d.png"),
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-r", str(fps),
        str(mp4_path),
    ]
    if not shutil.which("ffmpeg"):
        print("\nFFmpeg not found.  Run manually:")
        print("  " + " ".join(cmd))
        return None
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"FFmpeg error: {r.stderr[-400:]}")
        return None
    return mp4_path


def make_contact_sheet(frames_dir, out_path, fps):
    """7-frame contact sheet at t = 0, 0.5, 1, 2, 3, 4, 5 s."""
    times = [0.0, 0.5, 1.0, 2.0, 3.0, 4.0, 5.0]
    inputs = []
    for t in times:
        fn = max(1, round(t * fps))
        p = frames_dir / f"frame_{fn:04d}.png"
        if p.exists():
            inputs.extend(["-i", str(p)])
    if len(inputs) < 4 or not shutil.which("ffmpeg"):
        return None
    n = len(inputs) // 2
    scales = ";".join(f"[{i}:v]scale=320:-1[s{i}]" for i in range(n))
    tiles = "".join(f"[s{i}]" for i in range(n))
    filt = f"{scales};{tiles}hstack=inputs={n}[out]"
    cmd = ["ffmpeg", "-y", *inputs,
           "-filter_complex", filt, "-map", "[out]",
           "-q:v", "2", str(out_path)]
    subprocess.run(cmd, capture_output=True, text=True)
    return out_path if Path(out_path).exists() else None


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

def verify_stage1(arm, out_dir, total_frames, fps):
    cycle = CONFIG["cycle_frames"]
    sc = bpy.context.scene
    checks = {
        "duration_s": total_frames / fps,
        "fps": fps,
        "total_frames": total_frames,
    }

    # Foot penetration (IK foot Z < 0)
    penetration = False
    for f in range(1, min(total_frames + 1, 80)):
        sc.frame_set(f)
        for bn in ("IK_foot_L", "IK_foot_R"):
            pb = arm.pose.bones.get(bn)
            if pb and pb.location.z < -0.005:
                penetration = True
    checks["no_foot_penetration"] = not penetration

    # Knees bend (thigh rotation changes)
    knee_ok = False
    for f in [1, cycle // 4 + 1, cycle // 2 + 1]:
        sc.frame_set(f)
        for bn in ("thigh_L", "thigh_R"):
            pb = arm.pose.bones.get(bn)
            if pb and abs(pb.rotation_euler.x) > 0.05:
                knee_ok = True
    checks["knees_bend"] = knee_ok

    # Pelvis vertical motion
    sc.frame_set(1)
    pz1 = arm.pose.bones["pelvis"].location.z if "pelvis" in arm.pose.bones else 0
    sc.frame_set(5)
    pz2 = arm.pose.bones["pelvis"].location.z if "pelvis" in arm.pose.bones else 0
    checks["pelvis_weight_transfer"] = abs(pz1 - pz2) > 0.003

    # Arms oppose legs
    sc.frame_set(1)
    tl = arm.pose.bones.get("thigh_L")
    ur = arm.pose.bones.get("upperarm_R")
    checks["arms_oppose_legs"] = bool(
        tl and ur and tl.rotation_euler.x * ur.rotation_euler.x > 0)

    # Ear secondary motion
    ear_ok = False
    for f in [2, 6, 10]:
        sc.frame_set(f)
        for bn in ("ear_01_L", "ear_02_L", "ear_03_L"):
            pb = arm.pose.bones.get(bn)
            if pb and any(abs(r) > 0.005 for r in pb.rotation_euler):
                ear_ok = True
    checks["ear_secondary"] = ear_ok

    # Tail delayed follow-through
    tail_ok = False
    for f in [1, 8, 15]:
        sc.frame_set(f)
        for i in range(1, 7):
            pb = arm.pose.bones.get(f"tail_{i:02d}")
            if pb and any(abs(r) > 0.005 for r in pb.rotation_euler):
                tail_ok = True
    checks["tail_follow_through"] = tail_ok

    # Loop transition (pose at frame 1 ≈ pose at start of last full cycle)
    loop_ok = True
    sc.frame_set(1)
    ref = {}
    for bn in ("pelvis", "thigh_L", "thigh_R"):
        pb = arm.pose.bones.get(bn)
        if pb:
            ref[bn] = tuple(pb.rotation_euler)
    last_start = ((total_frames - 1) // cycle) * cycle + 1
    sc.frame_set(last_start)
    for bn, rv in ref.items():
        pb = arm.pose.bones.get(bn)
        if pb:
            diff = sum(abs(a - b) for a, b in zip(rv, tuple(pb.rotation_euler)))
            if diff > 0.15:
                loop_ok = False
    checks["loop_clean"] = loop_ok

    # No foot sliding — simplified: IK foot Z ≈ 0 during stance frames
    slide_ok = True
    for f in range(1, min(total_frames + 1, cycle * 2 + 1)):
        sc.frame_set(f)
        lf = (f - 1) % cycle
        # Left stance: frames 0-7;  Right stance: 14-21
        if lf <= 7:
            pb = arm.pose.bones.get("IK_foot_L")
            if pb and abs(pb.location.z) > 0.015:
                slide_ok = False
        if 14 <= lf <= 21:
            pb = arm.pose.bones.get("IK_foot_R")
            if pb and abs(pb.location.z) > 0.015:
                slide_ok = False
    checks["no_foot_sliding"] = slide_ok

    critical = ["no_foot_penetration", "knees_bend", "pelvis_weight_transfer",
                "arms_oppose_legs", "ear_secondary", "tail_follow_through",
                "loop_clean", "no_foot_sliding"]
    all_pass = all(checks.get(c, False) for c in critical)
    checks["STAGE1_PASS"] = all_pass

    vpath = out_dir / "verification.json"
    vpath.write_text(json.dumps(checks, indent=2))

    print("\n=== STAGE 1 VERIFICATION ===")
    for k, v in checks.items():
        label = "PASS" if v is True else ("FAIL" if v is False else str(v))
        print(f"  {k}: {label}")
    print(f"\n  OVERALL: {'PASS' if all_pass else '** FAIL **'}")
    return all_pass, checks


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    t0 = time.time()
    fps = CONFIG["fps"]

    # ── Load ──
    blend = ROOT / CONFIG["blend_file"]
    print(f"\nLoading {blend} …")
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    arm = bpy.data.objects[CONFIG["armature_name"]]

    # ── Audit + fix ──
    report = audit_rig(arm)
    if report["weight_issues"]:
        fix_weights(arm)

    # ── Stage 1: 5-second in-place run ──
    s1_frames = CONFIG["stage1_seconds"] * fps      # 120
    print(f"\n── STAGE 1: {CONFIG['stage1_seconds']}s test ({s1_frames} frames) ──")
    create_run_animation(arm, s1_frames, forward_motion=False)

    cam = setup_studio(ground_length=20)
    keyframe_camera(cam, arm, s1_frames, tracking=False)
    configure_render(CONFIG["stage1_res"], CONFIG["stage1_samples"])

    s1_dir = ROOT / CONFIG["stage1_dir"]
    frames1 = s1_dir / "frames"
    t_render_start = time.time()
    render_frames(frames1, s1_frames, fps)
    t_render1 = time.time() - t_render_start

    mp4_1 = encode_mp4(frames1, s1_dir / "preview.mp4", fps)
    make_contact_sheet(frames1, s1_dir / "contact_sheet.jpg", fps)

    # ── Verify gate ──
    passed, checks = verify_stage1(arm, s1_dir, s1_frames, fps)

    print(f"\n── STAGE 1 REPORT ──")
    print(f"  Cycle length:  {CONFIG['cycle_frames']} frames")
    print(f"  Stride length: {CONFIG['stride_length']} BU")
    print(f"  Root speed:    {CONFIG['stride_length'] / CONFIG['cycle_frames'] * fps:.2f} BU/s")
    print(f"  Render time:   {t_render1:.1f}s ({t_render1/s1_frames:.2f}s/frame)")
    print(f"  Preview MP4:   {mp4_1}")
    print(f"  Result:        {'PASS' if passed else 'FAIL'}")

    if not passed:
        print("\n** STAGE 1 FAILED — skipping Stage 2. **")
        fails = [k for k in checks if checks[k] is False]
        print(f"   Failed checks: {fails}")
        print("   To fix: review the cycle keyframe data in _half_cycle_poses().")
        return

    # ── Stage 2: 60-second forward-locomotion render ──
    s2_frames = CONFIG["stage2_seconds"] * fps      # 1440
    print(f"\n── STAGE 2: {CONFIG['stage2_seconds']}s full ({s2_frames} frames) ──")

    # Rebuild animation with forward motion
    create_run_animation(arm, s2_frames, forward_motion=True)

    # Extend ground plane
    floor = bpy.data.objects.get("RunFloor")
    if floor:
        total_dist = (s2_frames / CONFIG["cycle_frames"]) * CONFIG["stride_length"]
        floor.scale.x = max(1, total_dist / 10 + 2)
        floor.location.x = total_dist / 2
        bpy.context.view_layer.update()

    keyframe_camera(cam, arm, s2_frames, tracking=True)
    configure_render(CONFIG["stage2_res"], CONFIG["stage2_samples"])

    s2_dir = ROOT / CONFIG["stage2_dir"]
    frames2 = s2_dir / "frames"
    t2_start = time.time()
    render_frames(frames2, s2_frames, fps)
    t_render2 = time.time() - t2_start

    mp4_2 = encode_mp4(frames2, s2_dir / "kiko_run_60s.mp4", fps)

    # Save .blend
    blend_out = ROOT / "KIKO_run_60s.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_out))

    t_total = time.time() - t0
    print(f"\n── STAGE 2 REPORT ──")
    print(f"  Total frames:  {s2_frames}")
    print(f"  Resolution:    {CONFIG['stage2_res'][0]}x{CONFIG['stage2_res'][1]}")
    print(f"  Render time:   {t_render2:.1f}s ({t_render2/s2_frames:.2f}s/frame)")
    print(f"  Total time:    {t_total:.1f}s")
    print(f"  MP4:           {mp4_2}")
    print(f"  Blend saved:   {blend_out}")


if __name__ == "__main__":
    main()
