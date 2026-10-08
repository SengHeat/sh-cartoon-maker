#!/usr/bin/env python3
"""Resume Stage 2 render from frame 871 onward.

Re-creates the animation from kiko_run.py, then renders only
the remaining frames (871-1440) into the existing frames dir.

Run: blender --background --python kiko_run_resume.py
"""
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

_dir = os.path.dirname(os.path.abspath(__file__))
if _dir not in sys.path:
    sys.path.insert(0, _dir)

import bpy
import kiko_run

ROOT = Path.cwd()
FPS = 24
TOTAL = 1440
FRAMES_DIR = ROOT / "output" / "kiko_run_60s" / "frames"
MP4_PATH = ROOT / "output" / "kiko_run_60s" / "kiko_run_60s.mp4"
BLEND_OUT = ROOT / "KIKO_run_60s.blend"


def main():
    # Find where we stopped
    last = 0
    for p in sorted(FRAMES_DIR.glob("frame_*.png")):
        n = int(p.stem.split("_")[1])
        if n > last:
            last = n
    start = last + 1
    print(f"Last frame on disk: {last}  |  Resuming from: {start}")

    if start > TOTAL:
        print("All frames already rendered — skipping to encode.")
    else:
        # Rebuild scene + animation (same as kiko_run.py Stage 2)
        blend = ROOT / kiko_run.CONFIG["blend_file"]
        print(f"Loading {blend} …")
        bpy.ops.wm.open_mainfile(filepath=str(blend))
        arm = bpy.data.objects[kiko_run.CONFIG["armature_name"]]
        kiko_run.fix_weights(arm)
        kiko_run.create_run_animation(arm, TOTAL, forward_motion=True)
        cam = kiko_run.setup_studio(ground_length=200)
        kiko_run.keyframe_camera(cam, arm, TOTAL, tracking=True)
        kiko_run.configure_render(kiko_run.CONFIG["stage2_res"],
                                  kiko_run.CONFIG["stage2_samples"])

        # Render ONLY the missing frames
        sc = bpy.context.scene
        sc.frame_start = start
        sc.frame_end = TOTAL
        sc.render.fps = FPS
        sc.render.filepath = str(FRAMES_DIR) + "/frame_"

        t0 = time.time()
        bpy.ops.render.render(animation=True)
        elapsed = time.time() - t0
        rendered = TOTAL - start + 1
        print(f"Rendered {rendered} frames in {elapsed:.1f}s "
              f"({elapsed / max(rendered, 1):.2f}s/frame)")

        bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_OUT))

    # Encode full 1-1440 sequence
    actual = len(list(FRAMES_DIR.glob("frame_*.png")))
    print(f"\nTotal frames on disk: {actual}")

    cmd = [
        "ffmpeg", "-y",
        "-framerate", str(FPS),
        "-start_number", "1",
        "-i", str(FRAMES_DIR / "frame_%04d.png"),
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-r", str(FPS),
        str(MP4_PATH),
    ]
    if shutil.which("ffmpeg"):
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode == 0 and MP4_PATH.exists():
            mb = MP4_PATH.stat().st_size / (1024 * 1024)
            print(f"MP4: {MP4_PATH} ({mb:.1f} MB)")
        else:
            print(f"FFmpeg error: {r.stderr[-400:]}")
    else:
        print("FFmpeg not found. Run:\n  " + " ".join(cmd))

    print(f"\n── STAGE 2 FINAL ──")
    print(f"  Frames: {actual}/{TOTAL}")
    print(f"  Res:    1920x1080")
    print(f"  FPS:    {FPS}")
    if MP4_PATH.exists():
        print(f"  MP4:    {MP4_PATH}")
    if BLEND_OUT.exists():
        print(f"  Blend:  {BLEND_OUT}")


if __name__ == "__main__":
    main()
