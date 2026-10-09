"""Build, measure and render the Stage 4 eight-second acting gate."""
from __future__ import annotations

import json
import math
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import bpy
from mathutils import Vector

BLENDER_DIR = Path(__file__).resolve().parent
ROOT = BLENDER_DIR.parent
sys.path.insert(0, str(BLENDER_DIR))
import kiko_expressive_rig as rig

plan, e = rig.plan, rig.e
OUT = ROOT / "output/kiko_acting_test_8s"


def snapshot(ch, name):
    rig.pose(ch, name)
    return {pb.name: {"location": list(pb.location), "rotation_euler": list(pb.rotation_euler), "scale": list(pb.scale),
                      "properties": {k: pb[k] for k in pb.keys() if isinstance(pb[k], (int, float))}}
            for pb in ch.arm.pose.bones}


def main():
    source = BLENDER_DIR / "KIKO_master_v2.blend"
    previous = json.loads((ROOT / "output/kiko_v2_rig_test/verification.json").read_text())
    if previous["status"] != "PASS" or previous["master_sha256"] != plan.digest(source):
        raise RuntimeError("Stage 3 must pass for the current V2 master")
    OUT.mkdir(parents=True, exist_ok=True)
    dest = BLENDER_DIR / "KIKO_acting_test_8s.blend"
    plan.backup([source, dest, OUT / "verification.json", OUT / "preview.mp4"])
    report = {"status": "BUILDING", "pass": False, "source_sha256": plan.digest(source), "duration": 8,
              "fps": 24, "frame_count": 192, "resolution": [854, 480], "visual_review": "PENDING"}
    plan.dump(OUT / "verification.json", report)
    bpy.ops.wm.open_mainfile(filepath=str(source))
    arm = bpy.data.objects["KIKO_RIG_armature"]
    ch = SimpleNamespace(arm=arm, sole_z={s: arm["kiko_sole_z_" + s] for s in ("L", "R")})
    ch.geo = lambda name: bpy.data.objects["KIKO_GEO_" + name]
    sequence = [(1, "neutral"), (24, "neutral"), (36, "curious"), (48, "curious"),
                (60, "wave"), (72, "wave"), (84, "point"), (96, "point"),
                (108, "surprised"), (120, "surprised"), (132, "scared"), (144, "scared"),
                (156, "confident"), (168, "confident"), (180, "happy"), (192, "happy")]
    poses = {name: snapshot(ch, name) for _, name in sequence}
    rig.reset(ch)
    ad = arm.animation_data_create()
    ad.action = bpy.data.actions.new("KIKO_ACT_acting_test_8s")
    scene = bpy.context.scene
    scene.frame_start, scene.frame_end, scene.render.fps = 1, 192, 24
    scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = 854, 480, 100
    rig.camera(scene, False)
    for frame in range(1, 193):
        lo, hi = sequence[0], sequence[-1]
        for a, b in zip(sequence, sequence[1:]):
            if a[0] <= frame <= b[0]:
                lo, hi = a, b
                break
        weight = e.smooth((frame - lo[0]) / max(hi[0] - lo[0], 1))
        for pb in arm.pose.bones:
            a, b = poses[lo[1]][pb.name], poses[hi[1]][pb.name]
            for path in ("location", "rotation_euler", "scale"):
                # Jaw rotation is driven by its open slider, never baked over it.
                if pb.name == "CTRL_jaw" and path == "rotation_euler":
                    continue
                setattr(pb, path, [(1 - weight) * x + weight * y for x, y in zip(a[path], b[path])])
            for key in a["properties"]:
                pb[key] = (1 - weight) * a["properties"][key] + weight * b["properties"][key]
        t = (frame - 1) / 24
        bones = arm.pose.bones
        if 49 <= frame <= 72:
            bones["CTRL_hand_R"].rotation_euler.z += .25 * math.sin(math.tau * (frame - 49) / 8)
        if frame >= 169:
            fade = e.smooth((frame - 169) / 10)
            bones["CTRL_tail_base"].rotation_euler.z += .18 * fade * math.sin(math.tau * (frame - 169) / 15)
            bones["CTRL_tail_tip"].rotation_euler.z += .1 * fade * math.sin(math.tau * (frame - 173) / 15)
        for side in ("L", "R"):
            bones["CTRL_ear_" + side].rotation_euler.x += .02 * math.sin(math.tau * t * 2 - .8)
        blink = max(0., 1 - abs(frame - 18) / 3) if frame < 24 else max(0., 1 - abs(frame - 159) / 3)
        bones["CTRL_face"]["blink"] = blink
        bones["CTRL_face"]["squint"] *= 1 - blink
        for pb in bones:
            for path in ("location", "rotation_euler", "scale"):
                if pb.name != "CTRL_jaw" or path != "rotation_euler":
                    pb.keyframe_insert(path, frame=frame, group=pb.name)
            for key in pb.keys():
                if isinstance(pb[key], (int, float)):
                    pb.keyframe_insert(f'["{key}"]', frame=frame, group=pb.name)
    e.linear(ad.action)
    # Inspect the evaluated animation, not merely the requested control values.
    min_z, max_slide, max_ik = 1e6, 0., 0.
    previous_points = {}
    facial_movement, hand_heights = [], []
    for half in range(383):
        e.frame_at(1 + half / 2)
        facial_movement.append(arm.pose.bones["jaw"].matrix.translation.z)
        hand_heights.append(arm.pose.bones["hand_R"].head.z)
        for side in ("L", "R"):
            points = e.mesh_points(ch.geo("foot_" + side))
            for i in range(3):
                points += e.mesh_points(ch.geo(f"toe_{i}_{side}"))
            min_z = min(min_z, min(p.z for p in points))
            if side in previous_points:
                max_slide = max(max_slide, max((a - b).length for a, b in zip(points, previous_points[side])))
            previous_points[side] = points
            max_ik = max(max_ik, (arm.pose.bones["shin_" + side].tail - arm.pose.bones["IK_foot_" + side].head).length)
    checks = {"feet_above_floor": {"min_sole_z": min_z, "pass": min_z >= -.001},
              "planted_feet": {"max_half_frame_vertex_motion": max_slide, "pass": max_slide < .002},
              "ik_reach": {"max_error": max_ik, "pass": max_ik < .002},
              "raised_hand": {"maximum_height": max(hand_heights), "pass": max(hand_heights) > 1.6}}
    report.update(checks=checks, sequence=[{"frame": f, "pose": n} for f, n in sequence],
                  preview_path="output/kiko_acting_test_8s/preview.mp4", contact_sheet_path="output/kiko_acting_test_8s/contact_sheet.jpg",
                  blend_path="KIKO_acting_test_8s.blend", sampling="All 192 frames plus half frames for evaluated feet/IK; sampled visual review required for body/face/tail.")
    report["status"] = "RENDERING" if all(c["pass"] for c in checks.values()) else "FAIL"
    plan.dump(OUT / "verification.json", report)
    if report["status"] == "FAIL":
        raise RuntimeError("Acting gate failed before rendering")
    scene.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=str(dest))
    plan.render_frames(scene, OUT / "frames")
    cfg = {"scene": {"fps": 24, "duration_sec": 8}}
    preview = OUT / "preview.mp4"
    subprocess.run(e.encode_command(cfg, OUT / "frames", preview), check=True)
    probe = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries", "stream=codec_name,pix_fmt,width,height,r_frame_rate,nb_read_frames,duration", "-of", "json", str(preview)], text=True))["streams"][0]
    video_pass = (probe["codec_name"] == "h264" and probe["pix_fmt"] == "yuv420p" and probe["r_frame_rate"] == "24/1" and int(probe["nb_read_frames"]) == 192 and abs(float(probe["duration"]) - 8) < 1e-4 and [probe["width"], probe["height"]] == [854, 480])
    report.update(video=probe, video_pass=video_pass, source_unchanged=plan.digest(source) == report["source_sha256"],
                  status="AWAITING_VISUAL_REVIEW" if video_pass else "FAIL")
    subprocess.run([shutil.which("python3") or "python3", "-m", "cartoon_studio.kiko_review_sheet", "--output",
                    str(OUT / "contact_sheet.jpg"), "--columns", "4",
                    *[str(OUT / "frames" / f"frame_{f:06d}.png") for f in (12, 36, 60, 84, 108, 132, 156, 180)]], cwd=ROOT, check=True)
    if not report["source_unchanged"]:
        report["status"] = "FAIL"
    plan.dump(OUT / "verification.json", report)
    if report["status"] == "FAIL":
        raise RuntimeError("Acting video encoding/source integrity verification failed")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        path = OUT / "verification.json"
        report = json.loads(path.read_text()) if path.exists() else {}
        report.update(status="FAIL", **{"pass": False}, error=str(exc))
        plan.dump(path, report)
        raise
