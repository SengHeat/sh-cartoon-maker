#!/usr/bin/env python3
"""Render an animated 360-degree turntable of KIKO and encode to MP4.

Run headless:
    blender --background --python turntable_kiko.py

Builds the full KIKO scene (model, materials, lights) via build_kiko,
parents the camera to a rotating empty for a seamless orbit, renders
the frame sequence with Eevee, and encodes to H.264 MP4 via FFmpeg.
"""

import math
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

# Ensure build_kiko can be imported from the same directory.
_script_dir = os.path.dirname(os.path.abspath(__file__))
if _script_dir not in sys.path:
    sys.path.insert(0, _script_dir)

import bpy
from mathutils import Vector

import build_kiko

# -----------------------------------------------------------------------------
# Turntable configuration
# -----------------------------------------------------------------------------

CONFIG = {
    "turntable_frames": 120,
    "fps": 24,
    "resolution_x": 1080,
    "resolution_y": 1080,
    "render_samples": 48,
    "camera_distance": 6.8,
    "camera_height": 1.95,
    "camera_center_z": 1.85,
    "camera_lens_mm": 66,
    "frame_output_dir": "renders/turntable",
    "mp4_output": "renders/kiko_turntable.mp4",
}


# -----------------------------------------------------------------------------
# Scene setup (reuses build_kiko without rendering static views)
# -----------------------------------------------------------------------------

def build_scene():
    """Build the full KIKO scene — model, materials, lights, camera."""
    build_kiko.clean_scene()
    c = build_kiko.CONFIG["colors"]
    materials = {
        "teal": build_kiko.make_material("MAT_BODY_FUR_TEAL", c["body_teal"], 0.94, specular=0.20),
        "cream": build_kiko.make_material("MAT_Fur_Cream", c["fur_cream"], 0.94, specular=0.20),
        "orange": build_kiko.make_material("MAT_OrangeAccent", c["orange_accent"], 0.88),
        "inner_ear": build_kiko.make_material("MAT_InnerEar", c["ear_inner"], 0.84),
        "leather": build_kiko.make_material("MAT_LeatherBrown", c["leather_brown"], 0.78),
        "eye_white": build_kiko.make_material("MAT_EyeWhite", c["eye_white"], 0.28, specular=0.48),
        "iris": build_kiko.make_material("MAT_IrisBrown", c["iris_brown"], 0.30, specular=0.46),
        "eye_dark": build_kiko.make_material("MAT_EyeDark", c["eye_dark"], 0.24, specular=0.50),
        "nose": build_kiko.make_material("MAT_Nose", c["nose"], 0.52),
        "floor": build_kiko.make_material("MAT_StudioFloor", c["studio_floor"], 0.90),
    }
    materials["teal"]["is_body_fur_material"] = True
    build_kiko.build_character(materials)
    camera = build_kiko.setup_studio(materials)
    build_kiko.configure_render()
    return camera


# -----------------------------------------------------------------------------
# Turntable animation
# -----------------------------------------------------------------------------

def setup_turntable(camera):
    """Parent camera to a rotating empty for a seamless 360-degree orbit."""
    center_z = CONFIG["camera_center_z"]

    # Turntable pivot at KIKO's visual center.
    pivot = bpy.data.objects.new("KIKO_Turntable", None)
    pivot.empty_display_type = "PLAIN_AXES"
    pivot.empty_display_size = 0.3
    pivot.location = (0, 0, center_z)
    bpy.context.scene.collection.objects.link(pivot)

    # Camera orbits at configured distance and height.
    distance = CONFIG["camera_distance"]
    height_offset = CONFIG["camera_height"] - center_z
    camera.parent = pivot
    camera.location = (0, -distance, height_offset)
    look_dir = Vector((0, distance, -height_offset))
    camera.rotation_euler = look_dir.to_track_quat("-Z", "Y").to_euler()
    camera.data.lens = CONFIG["camera_lens_mm"]

    # Animate pivot: 0 at frame 1, full rotation one frame past the end
    # so the last rendered frame is distinct from the first (seamless loop).
    n = CONFIG["turntable_frames"]
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = n
    scene.render.fps = CONFIG["fps"]

    # Linear interpolation for constant rotation speed (set before inserting
    # keyframes — Blender 5.x layered actions don't expose action.fcurves).
    bpy.context.preferences.edit.keyframe_new_interpolation_type = "LINEAR"

    pivot.rotation_euler = (0, 0, 0)
    pivot.keyframe_insert(data_path="rotation_euler", index=2, frame=1)
    pivot.rotation_euler.z = math.tau
    pivot.keyframe_insert(data_path="rotation_euler", index=2, frame=n + 1)

    return pivot


def configure_turntable_render():
    """Override resolution and samples for the turntable sequence."""
    scene = bpy.context.scene
    scene.render.resolution_x = CONFIG["resolution_x"]
    scene.render.resolution_y = CONFIG["resolution_y"]
    scene.render.resolution_percentage = 100
    if hasattr(scene, "eevee") and hasattr(scene.eevee, "taa_render_samples"):
        scene.eevee.taa_render_samples = CONFIG["render_samples"]


# -----------------------------------------------------------------------------
# Rendering and encoding
# -----------------------------------------------------------------------------

def render_frames():
    """Clear old frames and render the turntable image sequence."""
    frame_dir = Path.cwd() / CONFIG["frame_output_dir"]
    if frame_dir.exists():
        shutil.rmtree(frame_dir)
    frame_dir.mkdir(parents=True, exist_ok=True)

    bpy.context.scene.render.filepath = str(frame_dir) + "/kiko_"
    bpy.ops.render.render(animation=True)
    return frame_dir


def encode_mp4(frame_dir):
    """Encode PNG sequence to H.264 MP4 via FFmpeg.

    If FFmpeg is not installed, prints the exact command for manual execution
    instead of crashing.
    """
    mp4_path = Path.cwd() / CONFIG["mp4_output"]
    mp4_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg", "-y",
        "-framerate", str(CONFIG["fps"]),
        "-start_number", "1",
        "-i", str(frame_dir / "kiko_%04d.png"),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-r", str(CONFIG["fps"]),
        str(mp4_path),
    ]

    if not shutil.which("ffmpeg"):
        print("\nFFmpeg not found. Run this command manually:")
        print("  " + " ".join(cmd))
        return None

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"\nFFmpeg failed (exit {result.returncode}):")
        print(result.stderr[-500:] if result.stderr else "(no stderr)")
        return None
    return mp4_path


# -----------------------------------------------------------------------------
# Entry point
# -----------------------------------------------------------------------------

def main():
    t_start = time.time()

    camera = build_scene()
    setup_turntable(camera)
    configure_turntable_render()
    frame_dir = render_frames()
    t_render = time.time() - t_start

    mp4_path = encode_mp4(frame_dir)
    t_total = time.time() - t_start

    frame_count = len(list(frame_dir.glob("kiko_*.png")))
    n = CONFIG["turntable_frames"]

    print("\n=== KIKO TURNTABLE SUMMARY ===")
    print(f"Frames rendered: {frame_count} / {n}")
    print(f"Resolution: {CONFIG['resolution_x']}x{CONFIG['resolution_y']}")
    print(f"FPS: {CONFIG['fps']}")
    print(f"Render time: {t_render:.1f}s ({t_render / max(frame_count, 1):.2f}s/frame)")
    print(f"Total time (incl. encode): {t_total:.1f}s")
    if mp4_path and mp4_path.exists():
        size_mb = mp4_path.stat().st_size / (1024 * 1024)
        print(f"MP4: {mp4_path} ({size_mb:.1f} MB)")
    else:
        print("MP4: not produced (see above)")


if __name__ == "__main__":
    main()
