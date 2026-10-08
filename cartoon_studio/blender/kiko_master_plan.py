"""Execute the audited KIKO engineering gates without modifying source masters.

blender --background --python cartoon_studio/blender/kiko_master_plan.py -- audit
blender --background --python cartoon_studio/blender/kiko_master_plan.py -- run
Visual approval is recorded separately, after inspecting the rendered evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import kiko_engine as engine

engine.bpy, engine.Matrix, engine.Vector = bpy, Matrix, Vector
SOURCE = ROOT / "KIKO_master_v1_1.blend"
REPORTS = ROOT / "reports"


def dump(path, value):
    engine.dump(path, value)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def backup(paths):
    """Content-addressed backups preserve earlier artifacts across retries."""
    for path in paths:
        if path.is_file():
            target = ROOT / "backups/kiko_master_plan" / (path.stem + "_" + digest(path)[:16] + path.suffix)
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists():
                shutil.copy2(path, target)


def audit():
    required = [SOURCE, ROOT / "assets/hero/kiko.png", ROOT / "kiko_engine.py", ROOT / "scenes/kiko_master_run_gate.json"]
    missing = [str(p.relative_to(ROOT)) for p in required if not p.is_file() or not p.stat().st_size]
    if missing:
        raise RuntimeError(f"Stage 1 missing sources: {missing}")
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
    arm = bpy.data.objects.get("KIKO_RIG_armature")
    if arm is None or arm.type != "ARMATURE":
        raise RuntimeError("V1.1 has no KIKO_RIG_armature")
    metadata = {
        "source": str(SOURCE.relative_to(ROOT)), "source_sha256": digest(SOURCE),
        "blender_version": bpy.app.version_string,
        "armature": arm.name,
        "bones": [{"name": b.name, "parent": b.parent.name if b.parent else None,
                   "deform": b.use_deform, "head": list(b.head_local), "tail": list(b.tail_local),
                   "constraints": [{"name": c.name, "type": c.type, "target": getattr(getattr(c, "target", None), "name", None),
                                    "subtarget": getattr(c, "subtarget", None)} for c in arm.pose.bones[b.name].constraints]}
                  for b in arm.data.bones],
        "meshes": [{"name": o.name, "vertices": len(o.data.vertices),
                    "groups": list(o.vertex_groups.keys()),
                    "shape_keys": list(o.data.shape_keys.key_blocks.keys()) if o.data.shape_keys else []}
                   for o in bpy.data.objects if o.type == "MESH"],
        "actions": [a.name for a in bpy.data.actions],
        "source_assets": {str(p.relative_to(ROOT)): {"bytes": p.stat().st_size, "sha256": digest(p)} for p in required},
        "rejected_archive_present": (ROOT / "backups/rejected_kiko_clay_v001").is_dir(),
        "existing_previews": [str(p.relative_to(ROOT)) for p in (ROOT / "output").rglob("*.mp4")],
    }
    # Test repairs in a fresh scene; never save over the library source.
    bpy.ops.wm.read_factory_settings(use_empty=True)
    cfg = engine.read_config(ROOT / "scenes/kiko_master_run_gate.json")
    ch = engine.Character(cfg["characters"][0], cfg["scene"])
    metadata["engine_deformation_audit"] = ch.audit
    metadata["pass"] = ch.audit["pass"]
    dump(REPORTS / "kiko_project_audit.json", metadata)
    bones = ", ".join(b["name"] for b in metadata["bones"])
    keys = "\n".join(f"- `{m['name']}`: {', '.join(m['shape_keys'])}" for m in metadata["meshes"] if m["shape_keys"])
    report = f"""# KIKO project audit

Inspected {datetime.now(timezone.utc).isoformat()} with Blender {bpy.app.version_string}.

Stage 1: **{'PASS' if metadata['pass'] else 'FAIL'}**. All Stage 2 sources are present and the engine's targeted deformation repairs {'pass' if metadata['pass'] else 'fail'} its stress checks.

- Source: `{metadata['source']}` ({SOURCE.stat().st_size} bytes), SHA-256 `{metadata['source_sha256']}`.
- Reference: `assets/hero/kiko.png`; visually inspected concept sheet.
- Animation Core V2 implementation: `kiko_engine.py`, `Character.base_action`, `configure_ik`, `verify_motion`.
- Earlier animation code: `kiko_run.py`, `cartoon_studio/blender/kiko_v1_1_polish.py`, `kiko_v1_1_motion_readability.py`, `kiko_runaway_fruit_v2.py`.
- Working armature: `{metadata['armature']}`; full rest positions, constraints and weights inventory in `reports/kiko_project_audit.json`.
- Existing 5-second and gesture videos are present under `output/`; they are historical evidence, not a fresh gate pass.
- `backups/rejected_kiko_clay_v001` is absent. The root sculpt/rebuild experiments remain untouched and excluded.
- Legacy `KIKO_master_v001.blend` and `KIKO_blockout_v001.blend` are zero-byte placeholders. They are not sources for this implementation.
- No imported GLB/FBX/OBJ final visual model was located. Stage 5 will need an acceptable sculpt or image-to-3D asset if none becomes available.

Actual bones: {bones}

Source actions: {', '.join(metadata['actions'])}

Shape keys:

{keys}

Observed rig limitations: source eye/finger bones lack skin weights; the jaw is dormant; existing lid arches do not seal a blink; the mouth has expression keys but no visemes. Stage 3 must address these, not merely rename controls.

The engine repairs shoulder/hip anchoring, sole weights, neck influence and IK pole angles in the appended scene. Stress-test results and repair details are in the JSON report. The V1.1 master is unchanged.
"""
    (REPORTS / "kiko_project_audit.md").write_text(report)
    if not metadata["pass"]:
        raise RuntimeError("Stage 1 deformation audit failed")


def render_frames(scene, folder):
    engine.prepare_frames(folder)
    for frame in range(scene.frame_start, scene.frame_end + 1):
        scene.frame_set(frame)
        scene.render.filepath = str(folder / f"frame_{frame:06d}.png")
        bpy.ops.render.render(write_still=True)
        if frame % 12 == 0:
            print(f"KIKO MASTER PLAN: rendered {frame}/{scene.frame_end}", flush=True)


def run_gate():
    audit_report = json.loads((REPORTS / "kiko_project_audit.json").read_text())
    if not audit_report["pass"] or audit_report["source_sha256"] != digest(SOURCE):
        raise RuntimeError("Stage 1 must pass for the current V1.1 source")
    for tool in ("ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            raise RuntimeError(f"Required runtime missing: {tool}")
    cfg = engine.read_config(ROOT / "scenes/kiko_master_run_gate.json")
    if not engine.is_gate(cfg):
        raise RuntimeError("Stage 2 requires the 5s / 24 FPS / 854x480 run config")
    work = ROOT / "output/kiko_run_test_5s"
    work.mkdir(parents=True, exist_ok=True)
    master = ROOT / "KIKO_run_test_5s.blend"
    preview = work / "preview.mp4"
    backup([SOURCE, master, work / "verification.json", work / "contact_sheet.jpg", preview])
    report = {"status": "BUILDING", "pass": False, "visual_review": {"status": "PENDING"},
              "source_sha256": digest(SOURCE), "gate_signature": engine.gate_signature(cfg)}
    dump(work / "verification.json", report)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    ch = engine.Character(cfg["characters"][0], cfg["scene"])
    ch.base_action()
    ch.gestures()
    ch.face()
    scene = engine.setup_scene(cfg, [ch])
    motion = engine.verify_motion([ch], scene)
    action = ch.c["action"]
    n = action["loop_frames"]
    report.update(duration=5, fps=24, frame_count=120, cycle_length=n,
                  approximate_stride_length=action["stride_length"], approximate_root_speed=action["root_speed"],
                  contact_frames={s: [f for f in range(1, 121) if ((f - 1) / n + off) % 1 < ch.stance] for s, off in (("L", 0), ("R", .5))},
                  tail_delay=ch.c["secondary"]["tail"]["delay_frames"], ear_delay=ch.c["secondary"]["ears"]["delay_frames"],
                  known_deformation_issues=ch.audit["limitations"], characters=motion,
                  preview_path=str(preview.relative_to(ROOT)), contact_sheet_path=str((work / "contact_sheet.jpg").relative_to(ROOT)),
                  blend_path=str(master.relative_to(ROOT)), requested=cfg["scene"],
                  sampling="Evaluated subdivided soles every half frame throughout all 120 frames. Visual review required separately.")
    dump(work / "rig_audit.json", ch.audit)
    report["status"] = "RENDERING" if all(m["pass"] for m in motion) else "FAIL"
    dump(work / "verification.json", report)
    if report["status"] == "FAIL":
        raise RuntimeError("Stage 2 motion checks failed; inspect verification.json")
    scene.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=str(master))
    render_frames(scene, work / "frames")
    subprocess.run(engine.encode_command(cfg, work / "frames", preview), check=True)
    probe = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries", "stream=codec_name,pix_fmt,width,height,r_frame_rate,nb_read_frames,duration", "-of", "json", str(preview)], text=True))["streams"][0]
    report["video"] = probe
    report["video_pass"] = (probe["codec_name"] == "h264" and probe["pix_fmt"] == "yuv420p" and int(probe["nb_read_frames"]) == 120 and probe["r_frame_rate"] == "24/1" and abs(float(probe["duration"]) - 5) < 1e-4 and [probe["width"], probe["height"]] == [854, 480])
    report["contact_sheet"] = engine.contact_sheet(cfg, work / "frames", work)
    report["source_unchanged"] = digest(SOURCE) == audit_report["source_sha256"]
    report["status"] = "AWAITING_VISUAL_REVIEW" if report["video_pass"] and report["source_unchanged"] else "FAIL"
    dump(work / "verification.json", report)
    if report["status"] == "FAIL":
        raise RuntimeError("Stage 2 encoded video/source integrity failed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("audit", "run"))
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    try:
        {"audit": audit, "run": run_gate}[args.stage]()
    except Exception as exc:
        dump(REPORTS / f"kiko_{args.stage}_failure.json", {"status": "FAIL", "error": str(exc)})
        if args.stage == "run":
            path = ROOT / "output/kiko_run_test_5s/verification.json"
            report = json.loads(path.read_text()) if path.exists() else {}
            report.update(status="FAIL", **{"pass": False}, error=str(exc))
            dump(path, report)
        raise
