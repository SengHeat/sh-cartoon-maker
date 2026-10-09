#!/usr/bin/env python3
"""KIKO V1.1 JSON animation engine. Run with Blender, not system Python.

blender --background --python kiko_engine.py -- scenes/run_test_5s.json
Operational diagnostics: --audit-only or --build-only after the JSON path.
No external Python packages; Blender + FFmpeg/FFprobe are sufficient.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import shlex
import shutil
import subprocess
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TAU = math.tau
GESTURES = ("nod", "head_turn", "look_around", "wave", "point", "crouch",
            "body_turn", "ear_flick", "tail_flick")
FACING = {"east": math.pi / 2, "west": -math.pi / 2, "north": math.pi, "south": 0}
EAR_BONES = [f"ear_{i:02d}" for i in range(1, 4)]
TAIL_BONES = [f"tail_{i:02d}" for i in range(1, 7)]
REPORT_PATH = None


class EngineError(Exception):
    pass


def fail(path, message):
    raise EngineError(f"{path}: {message}")


def fields(value, path, required, optional=()):
    if not isinstance(value, dict):
        fail(path, "must be an object")
    for key in required:
        if key not in value:
            fail(f"{path}.{key}", "missing required field")
    for key in value:
        if key not in (*required, *optional):
            fail(f"{path}.{key}", "unknown field")


def number(value, path, lo, hi, integer=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        fail(path, "must be a finite number")
    if integer and type(value) is not int:
        fail(path, "must be an integer")
    if not lo <= value <= hi:
        fail(path, f"must be between {lo} and {hi}")


def choice(value, path, choices):
    if not isinstance(value, str) or value not in choices:
        fail(path, "supported values: " + ", ".join(choices))


def boolean(value, path):
    if type(value) is not bool:
        fail(path, "must be true or false")


def vector(value, path, count, lo, hi, integer=False):
    if not isinstance(value, list) or len(value) != count:
        fail(path, f"must be an array of {count} numbers")
    for i, v in enumerate(value):
        number(v, f"{path}[{i}]", lo, hi, integer)


def read_config(path):
    def unique(pairs):
        d = {}
        for k, v in pairs:
            if k in d:
                fail(f"JSON.{k}", "duplicate field")
            d[k] = v
        return d
    try:
        cfg = json.loads(path.read_text(), object_pairs_hook=unique)
    except (OSError, json.JSONDecodeError) as exc:
        fail(str(path), str(exc))
    validate(cfg)
    return cfg


def validate(c):
    fields(c, "$", ("scene", "environment", "camera", "characters", "output"))
    s = c["scene"]
    fields(s, "scene", ("duration_sec", "fps", "resolution", "samples", "engine"))
    number(s["duration_sec"], "scene.duration_sec", .1, 600)
    number(s["fps"], "scene.fps", 12, 60, True)
    vector(s["resolution"], "scene.resolution", 2, 64, 3840, True)
    if any(n % 2 for n in s["resolution"]):
        fail("scene.resolution", "H.264 yuv420p requires even width and height")
    number(s["samples"], "scene.samples", 1, 256, True)
    choice(s["engine"], "scene.engine", ("EEVEE",))
    if abs(s["duration_sec"] * s["fps"] - round(s["duration_sec"] * s["fps"])) > 1e-7:
        fail("scene.duration_sec", "duration_sec * fps must be an integer frame count")
    e = c["environment"]
    fields(e, "environment", ("ground", "background"))
    boolean(e["ground"], "environment.ground")
    choice(e["background"], "environment.background", ("neutral",))
    cam = c["camera"]
    fields(cam, "camera", ("type", "target", "angle", "distance", "height"))
    choice(cam["type"], "camera.type", ("tracking", "static"))
    choice(cam["angle"], "camera.angle", ("side", "3-4", "front"))
    number(cam["distance"], "camera.distance", 4, 500)
    number(cam["height"], "camera.height", .2, 50)
    chars = c["characters"]
    if not isinstance(chars, list) or not 1 <= len(chars) <= 8:
        fail("characters", "must contain 1–8 KIKO instances")
    ids = set()
    for i, ch in enumerate(chars):
        p = f"characters[{i}]"
        fields(ch, p, ("id", "model", "armature", "position", "facing", "action", "secondary", "face"), ("gestures",))
        if not isinstance(ch["id"], str) or not re.fullmatch(r"[a-z][a-z0-9_]{0,31}", ch["id"]):
            fail(p + ".id", "use 1–32 lowercase letters, digits, underscores; start with a letter")
        if ch["id"] in ids:
            fail(p + ".id", "duplicate character id")
        ids.add(ch["id"])
        choice(ch["model"], p + ".model", ("KIKO_master_v1_1.blend",))
        if not (ROOT / ch["model"]).is_file():
            fail(p + ".model", f"file not found: {ROOT / ch['model']}")
        choice(ch["armature"], p + ".armature", ("KIKO_RIG_armature",))
        vector(ch["position"], p + ".position", 3, -1000, 1000)
        if ch["position"][2] != 0:
            fail(p + ".position[2]", "must be 0 for the V1.1 flat-ground locomotion solver")
        choice(ch["facing"], p + ".facing", tuple(FACING))
        a = ch["action"]
        fields(a, p + ".action", ("type", "loop_frames", "stride_length", "root_speed", "pelvis_bounce", "forward_lean_deg", "squash_stretch"))
        choice(a["type"], p + ".action.type", ("run", "walk", "idle"))
        number(a["loop_frames"], p + ".action.loop_frames", 12, 120, True)
        if a["loop_frames"] % 2:
            fail(p + ".action.loop_frames", "must be even for symmetric left/right cycles")
        number(a["stride_length"], p + ".action.stride_length", 0, 1.6)
        number(a["root_speed"], p + ".action.root_speed", 0, 4)
        number(a["pelvis_bounce"], p + ".action.pelvis_bounce", 0, .15)
        number(a["forward_lean_deg"], p + ".action.forward_lean_deg", 0, 18)
        number(a["squash_stretch"], p + ".action.squash_stretch", 0, .1)
        if a["type"] == "idle":
            if a["stride_length"] != 0 or a["root_speed"] != 0:
                fail(p + ".action", "idle requires stride_length=0 and root_speed=0")
        else:
            expected = a["stride_length"] * s["fps"] / a["loop_frames"]
            if a["stride_length"] <= 0 or abs(a["root_speed"] - expected) > 1e-6:
                fail(p + ".action.root_speed", f"must equal stride_length * fps / loop_frames = {expected:.9f}; inconsistent speed causes foot sliding")
            if a["type"] == "walk" and a["stride_length"] > 1:
                fail(p + ".action.stride_length", "walk is limited to 1.0 unit per cycle")
        sec = ch["secondary"]
        fields(sec, p + ".secondary", ("ears", "tail"))
        for name, amount, names in (("ears", "bounce", EAR_BONES), ("tail", "follow_through", TAIL_BONES)):
            d = sec[name]
            q = p + ".secondary." + name
            fields(d, q, ("bones", "delay_frames", amount))
            if d["bones"] != names and not (name == "tail" and d["bones"] == ["tail_01..tail_06"]):
                fail(q + ".bones", f"must be {names}" + (' or ["tail_01..tail_06"]' if name == "tail" else ""))
            number(d["delay_frames"], q + ".delay_frames", 0, a["loop_frames"] / 2)
            number(d[amount], q + "." + amount, 0, .4)
        fields(ch["face"], p + ".face", ("expression", "blink"))
        choice(ch["face"]["expression"], p + ".face.expression", ("neutral", "happy", "surprised"))
        boolean(ch["face"]["blink"], p + ".face.blink")
        gs = ch.get("gestures", [])
        if not isinstance(gs, list):
            fail(p + ".gestures", "must be an array (empty is valid)")
        for j, g in enumerate(gs):
            q = f"{p}.gestures[{j}]"
            fields(g, q, ("type", "start_sec", "duration_sec", "intensity", "ease"))
            choice(g["type"], q + ".type", GESTURES)
            number(g["start_sec"], q + ".start_sec", 0, s["duration_sec"])
            number(g["duration_sec"], q + ".duration_sec", 4 / s["fps"], s["duration_sec"])
            if g["start_sec"] + g["duration_sec"] > s["duration_sec"] + 1e-7:
                fail(q + ".duration_sec", "gesture ends after scene.duration_sec")
            number(g["intensity"], q + ".intensity", 0, 1)
            choice(g["ease"], q + ".ease", ("smooth", "sharp"))
    choice(cam["target"], "camera.target", tuple(sorted(ids)))
    o = c["output"]
    fields(o, "output", ("mp4_path", "save_blend"))
    boolean(o["save_blend"], "output.save_blend")
    if not isinstance(o["mp4_path"], str):
        fail("output.mp4_path", "must be a relative output/*.mp4 path")
    dest = Path(o["mp4_path"])
    if dest.is_absolute() or ".." in dest.parts or len(dest.parts) < 2 or dest.parts[0] != "output" or dest.suffix != ".mp4":
        fail("output.mp4_path", "must be a relative .mp4 path below output/, without '..'")
    resolved = (ROOT / dest).resolve()
    if not resolved.is_relative_to(ROOT / "output"):
        fail("output.mp4_path", "symlinks must not escape the project's output directory")


def dump(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")


def curves(action, slot=None):
    """Layered-action API (Blender 4.4–5.x), plus legacy 4.x actions."""
    if hasattr(action, "layers") and len(action.layers):
        for layer in action.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    if slot is None or bag.slot_handle == slot.handle:
                        yield from bag.fcurves
    elif hasattr(action, "fcurves"):
        yield from action.fcurves


def linear(action):
    for fc in curves(action):
        for k in fc.keyframe_points:
            k.interpolation = "LINEAR"


def smooth(t):
    t = max(0., min(1., t))
    return t * t * (3 - 2 * t)


def bone_location(pb, world_delta):
    # Bone local Y is along its length; local Z is NOT world up.
    return pb.bone.matrix_local.to_3x3().inverted() @ Vector(world_delta)


def set_weight(obj, index, weights):
    for group in obj.vertex_groups:
        group.remove([index])
    for name, weight in weights.items():
        if weight > 1e-8:
            vg = obj.vertex_groups.get(name) or obj.vertex_groups.new(name=name)
            vg.add([index], weight, "REPLACE")


def mesh_points(obj):
    ev = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    me = ev.to_mesh()
    try:
        return [ev.matrix_world @ v.co for v in me.vertices]
    finally:
        ev.to_mesh_clear()


class Character:
    def __init__(self, config, scene_config):
        self.c, self.s = config, scene_config
        self.id = config["id"]
        # Append each instance separately: Blender remaps parents, armature modifiers,
        # actions and IK targets within this library load, never global bone lookups.
        with bpy.data.libraries.load(str(ROOT / config["model"]), link=False) as (src, dst):
            dst.objects = [n for n in src.objects if n == config["armature"] or n.startswith(("KIKO_GEO_", "KIKO_OUTFIT_"))]
        self.objects = {}
        collection = bpy.data.collections.new(self.id)
        bpy.context.scene.collection.children.link(collection)
        for obj in dst.objects:
            if obj is None:
                continue
            original = re.sub(r"\.\d{3}$", "", obj.name)
            self.objects[original] = obj
            collection.objects.link(obj)
            obj.name = f"{self.id}::{original}"
        self.arm = self.objects.get(config["armature"])
        if self.arm is None:
            fail(f"characters.{self.id}.armature", "armature missing in model")
        required = ["root", "pelvis", "spine_01", "spine_02", "chest", "neck", "head", "CTRL_root", "CTRL_COG", "eye_aim"] + TAIL_BONES
        for side in ("L", "R"):
            required += [f"{b}_{side}" for b in ("clavicle", "upperarm", "lowerarm", "hand", "thigh", "shin", "foot", "toe", "IK_foot", "POLE_knee", "eye", *EAR_BONES)]
        missing = sorted(set(required) - set(self.arm.pose.bones.keys()))
        if missing:
            fail(f"characters.{self.id}.armature", "missing bones: " + ", ".join(missing))
        self.face_curves = {}
        for name, obj in self.objects.items():
            ad = obj.animation_data
            if ad and ad.action and obj != self.arm:
                self.face_curves[name] = [(fc.data_path, fc.array_index, fc.evaluate(202), fc.evaluate(240)) for fc in curves(ad.action, ad.action_slot)]
                # Sample source neutral, before discarding the inherited showcase timeline.
                for path, idx, _, neutral in self.face_curves[name]:
                    if path in ("location", "rotation_euler", "scale"):
                        getattr(obj, path)[idx] = neutral
            obj.animation_data_clear()
            if obj.type == "MESH" and obj.data.shape_keys:
                obj.data.shape_keys.animation_data_clear()
                for key in obj.data.shape_keys.key_blocks:
                    key.value = 0
        self.arm.location = (0, 0, 0)
        self.arm.rotation_euler = (0, 0, 0)
        self.arm.scale = (1, 1, 1)
        for pb in self.arm.pose.bones:
            pb.rotation_mode = "XYZ"
            pb.matrix_basis = Matrix.Identity(4)
        self.arm.data.pose_position = "REST"
        bpy.context.view_layer.update()
        self.audit = self.audit_and_repair()
        self.arm.data.pose_position = "POSE"
        self.configure_ik(collection)
        self.arm.rotation_euler.z = FACING[config["facing"]]
        self.arm.location = config["position"]
        bpy.context.view_layer.update()

    def geo(self, short):
        name = "KIKO_GEO_" + short
        if name not in self.objects:
            fail(f"characters.{self.id}.model", f"required object {name} missing")
        return self.objects[name]

    def audit_and_repair(self):
        arm = self.arm
        report = {"character": self.id, "model": self.c["model"], "bones": list(arm.data.bones.keys()),
                  "repairs": [], "weight_errors": [], "rig_rebuilt": False,
                  "source_file_modified": False,
                  "limitations": ["CTRL_root/CTRL_COG/CTRL_head and eye_aim have no source constraints; animate the deform chain directly",
                                  "eye and finger bones have no skin weights; gaze uses head/neck; wave/point use the existing whole paw",
                                  "dormant jaw is unused; no visemes or lip sync",
                                  "blink is the existing upper-lid arch motion, not a sealed eyelid"]}
        for name, obj in self.objects.items():
            if obj.type != "MESH" or obj.parent_type == "BONE":
                continue
            mods = [m for m in obj.modifiers if m.type == "ARMATURE"]
            if not mods or any(m.object != arm for m in mods):
                report["weight_errors"].append(name + ": missing or foreign armature modifier")
                continue
            for v in obj.data.vertices:
                total = sum(g.weight for g in v.groups if obj.vertex_groups[g.group].name in arm.data.bones and arm.data.bones[obj.vertex_groups[g.group].name].use_deform)
                if abs(total - 1) > 1e-4:
                    report["weight_errors"].append(f"{name}.vertices[{v.index}]: deform weight sum {total}")
        # The source uses inverse-distance-to-center weights, leaking forearm/shin
        # influence into joint roots and neck influence into the entire face.
        # Replace only the affected region weights; never change mesh coordinates.
        for side in ("L", "R"):
            for part in ("arm", "leg"):
                obj = self.geo(part + "_" + side)
                top = 1.52 if part == "arm" else .86
                knee = 1.20 if part == "arm" else .48
                parent = "clavicle_" + side if part == "arm" else "pelvis"
                upper = ("upperarm_" if part == "arm" else "thigh_") + side
                lower = ("lowerarm_" if part == "arm" else "shin_") + side
                end = ("hand_" if part == "arm" else "foot_") + side
                before = [{obj.vertex_groups[g.group].name: round(g.weight, 5) for g in v.groups} for v in obj.data.vertices if (obj.matrix_world @ v.co).z > top - .03][:3]
                for v in obj.data.vertices:
                    z = (obj.matrix_world @ v.co).z
                    anchor = smooth((z - (top - .16)) / .16)
                    bend = smooth((z - (knee - .10)) / .20)
                    end_z = .91 if part == "arm" else .16
                    tip = 1 - smooth((z - end_z) / .10)
                    rem = (1 - anchor) * (1 - tip)
                    set_weight(obj, v.index, {parent: anchor, upper: rem * bend, lower: rem * (1 - bend), end: (1 - anchor) * tip})
                report["repairs"].append({"mesh": obj.name, "region": "shoulder" if part == "arm" else "hip", "before_top_weights": before, "fix": "parent anchor; smooth adjacent-joint weights; normalized"})
            # Rigid cartoon paws: all visible sole vertices must follow the planted foot.
            obj = self.geo("foot_" + side)
            for v in obj.data.vertices:
                set_weight(obj, v.index, {"foot_" + side: 1})
            report["repairs"].append({"mesh": obj.name, "region": "sole", "fix": "remove shin/thigh influence so the planted paw cannot shear or slide"})
        for name, obj in self.objects.items():
            if obj.type != "MESH" or obj.parent_type == "BONE" or not {"head", "neck"}.issubset(obj.vertex_groups.keys()):
                continue
            for v in obj.data.vertices:
                z = (obj.matrix_world @ v.co).z
                h = smooth((z - 1.68) / .22) if name == "KIKO_GEO_head" else 1
                set_weight(obj, v.index, {"head": h, "neck": 1 - h})
            report["repairs"].append({"mesh": obj.name, "region": "neck/head", "fix": "blend only at neck seam; head and facial features follow head together"})
        # Measure actual edge distortion under isolated shoulder/hip/neck stress poses.
        arm.data.pose_position = "POSE"
        constraints = [c for p in arm.pose.bones for c in p.constraints]
        states = [c.mute for c in constraints]
        for c in constraints:
            c.mute = True
        bpy.context.view_layer.update()
        stress = []
        for short, bone, angle in (("arm_L", "upperarm_L", .6), ("arm_R", "upperarm_R", -.6), ("leg_L", "thigh_L", .6), ("leg_R", "thigh_R", -.6), ("head", "head", .35)):
            obj = self.geo(short)
            ref = mesh_points(obj)
            pb = arm.pose.bones[bone]
            pb.rotation_euler.x = angle
            bpy.context.view_layer.update()
            posed = mesh_points(obj)
            ev = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
            me = ev.to_mesh()
            ratios = []
            for edge in me.edges:
                i, j = edge.vertices
                d = (ref[i] - ref[j]).length
                if d > 1e-5:
                    ratios.append((posed[i] - posed[j]).length / d)
            ev.to_mesh_clear()
            stress.append({"mesh": obj.name, "bone": bone, "rotation_rad": angle,
                           "min_edge_ratio": min(ratios), "max_edge_ratio": max(ratios),
                           "pass": min(ratios) > .2 and max(ratios) < 2.5})
            pb.rotation_euler.x = 0
            bpy.context.view_layer.update()
        for c, state in zip(constraints, states):
            c.mute = state
        report["deformation_stress_tests"] = stress
        report["pass"] = not report["weight_errors"] and all(t["pass"] for t in stress)
        return report

    def configure_ik(self, collection):
        arm = self.arm
        arm.data.pose_position = "REST"
        bpy.context.view_layer.update()
        self.sole_z = {}
        for side in ("L", "R"):
            foot = arm.pose.bones["foot_" + side]
            # Include toes, not merely the ankle or an IK marker.
            points = mesh_points(self.geo("foot_" + side))
            for i in range(3):
                points += mesh_points(self.geo(f"toe_{i}_{side}"))
            self.sole_z[side] = min(p.z for p in points)
            # Existing shin IK remains in charge; orient the existing foot parallel
            # to its rest sole. No bones, mesh topology or rest pose are rebuilt.
            orient = bpy.data.objects.new(f"{self.id}::sole_orientation_{side}", None)
            collection.objects.link(orient)
            orient.parent = arm
            orient.rotation_euler = foot.bone.matrix_local.to_euler()
            con = foot.constraints.new("COPY_ROTATION")
            con.name = "KIKO engine planted sole orientation"
            con.target = orient
            con.target_space = "WORLD"
            con.owner_space = "WORLD"
            iks = [c for c in arm.pose.bones["shin_" + side].constraints if c.type == "IK"]
            if len(iks) != 1 or iks[0].target != arm or iks[0].subtarget != "IK_foot_" + side:
                fail(f"characters.{self.id}.armature.shin_{side}", "expected one existing two-bone foot IK constraint")
            ik = iks[0]
            ik.chain_count = 2
            ik.use_stretch = False
            ik.influence = 1
            arm.pose.bones["thigh_" + side].ik_stretch = 0
            arm.pose.bones["shin_" + side].ik_stretch = 0
        arm.data.pose_position = "POSE"
        arm.pose.bones["pelvis"].location = bone_location(arm.pose.bones["pelvis"], (0, 0, -.12))
        for side in ("L", "R"):
            pb = arm.pose.bones["IK_foot_" + side]
            ankle = arm.data.bones["foot_" + side].head_local.copy()
            ankle.z -= self.sole_z[side]
            pb.location = bone_location(pb, ankle - pb.bone.head_local)
        # Calibrate the source's zero pole angle numerically once, in neutral pose.
        # Choose the knee facing -Y (KIKO's forward), not sideways or backwards.
        for side in ("L", "R"):
            ik = next(c for c in arm.pose.bones["shin_" + side].constraints if c.type == "IK")
            candidates = []
            for n in range(72):
                angle = -math.pi + TAU * n / 72
                ik.pole_angle = angle
                bpy.context.view_layer.update()
                knee = arm.pose.bones["shin_" + side].head
                candidates.append((knee.y + 3 * abs(knee.x - arm.data.bones["shin_" + side].head_local.x), angle))
            ik.pole_angle = min(candidates)[1]
            self.audit.setdefault("ik_calibration", {})[side] = {"pole_angle_rad": ik.pole_angle, "rest_sole_min_z": self.sole_z[side]}
        arm.pose.bones["pelvis"].location = (0, 0, 0)

    def key(self, name, frame, rotation=None, translation=None, scale=None):
        pb = self.arm.pose.bones[name]
        if rotation is not None:
            pb.rotation_euler = rotation
            pb.keyframe_insert("rotation_euler", frame=frame, group=name)
        if translation is not None:
            pb.location = bone_location(pb, translation)
            pb.keyframe_insert("location", frame=frame, group=name)
        if scale is not None:
            pb.scale = scale
            pb.keyframe_insert("scale", frame=frame, group=name)

    def strip(self, action, label, start, end=None, repeat=1, additive=False):
        ad = self.arm.animation_data
        slot = ad.action_slot
        ad.action = None
        track = ad.nla_tracks.new()
        track.name = label
        strip = track.strips.new(label, int(start), action)
        if hasattr(strip, "action_slot"):
            strip.action_slot = slot
        strip.frame_start = start
        strip.blend_type = "ADD" if additive else "REPLACE"
        strip.extrapolation = "NOTHING"
        strip.use_auto_blend = False
        strip.repeat = repeat
        if end is not None:
            strip.frame_end = end
        return strip

    def base_action(self):
        a = self.c["action"]
        n = a["loop_frames"]
        ad = self.arm.animation_data_create()
        action = bpy.data.actions.new(f"{self.id}::base_{a['type']}")
        ad.action = action
        for pb in self.arm.pose.bones:
            pb.matrix_basis = Matrix.Identity(4)
        # Sample ONE cycle, with explicit contact transitions. Repeat using NLA.
        stance = .36 if a["type"] == "run" else .62
        self.stance = stance
        times = {i / 2 for i in range(2 * n + 1)}
        times.update((stance * n, ((stance + .5) % 1) * n))
        for f in sorted(times):
            phase = f / n
            q = TAU * phase
            idle = a["type"] == "idle"
            # Run compression belongs in early stance; the high point belongs
            # between toe-off and opposite contact, while both feet are airborne.
            bounce_phase = q - TAU * .18 if a["type"] == "run" else q
            bounce = a["pelvis_bounce"] * (.5 - .5 * math.cos(2 * bounce_phase))
            shift = (0 if idle else .035) * math.cos(q - math.pi * stance)
            # Keep a bent-knee reserve when the body rises into flight, so the
            # planted ankle remains inside the two-bone IK chain's reach.
            pelvis_drop = -.18 if a["type"] == "run" else -.13
            self.key("pelvis", f + 1, rotation=(0, 0, .018 * math.sin(q)), translation=(shift, 0, pelvis_drop + bounce))
            lean = math.radians(a["forward_lean_deg"])
            self.key("spine_01", f + 1, rotation=(lean * .65, 0, 0))
            self.key("spine_02", f + 1, rotation=(lean * .35, 0, -.022 * math.sin(q)))
            ss = a["squash_stretch"] * math.cos(2 * q)
            self.key("chest", f + 1, rotation=(-lean * .15, 0, .022 * math.sin(q)), scale=(1 + ss / 2, 1 - ss, 1 + ss / 2))
            self.key("neck", f + 1, rotation=(-lean * .3, 0, 0))
            self.key("head", f + 1, rotation=(-lean * .4, 0, 0))
            for side, offset in (("L", 0), ("R", .5)):
                p = (phase + offset) % 1
                if idle:
                    y, lift = 0, 0
                elif p <= stance:
                    # Root advances +speed; foot offsets cancel it exactly in stance.
                    y = a["stride_length"] * (p - stance / 2)
                    lift = 0
                else:
                    u = (p - stance) / (1 - stance)
                    length = a["stride_length"]
                    # Cubic Hermite: continuous velocity at lift-off and landing.
                    h = 3 * u * u - 2 * u ** 3
                    y = length * stance / 2 * (1 - 2 * h) + length * (1 - stance) * (2 * u ** 3 - 3 * u * u + u)
                    lift = (.16 if a["type"] == "run" else .07) * math.sin(math.pi * u) ** 2
                pb = self.arm.pose.bones["IK_foot_" + side]
                ankle = self.arm.data.bones["foot_" + side].head_local.copy()
                ankle.y += y
                ankle.z += lift - self.sole_z[side] + .003
                self.key(pb.name, f + 1, translation=ankle - pb.bone.head_local)
                arm_swing = 0 if idle else -1.8 * y
                self.key("upperarm_" + side, f + 1, rotation=(arm_swing, 0, 0))
                self.key("lowerarm_" + side, f + 1, rotation=(.32 + .08 * math.sin(TAU * p), 0, 0))
                self.key("hand_" + side, f + 1, rotation=(.04 * math.sin(TAU * p), 0, 0))
            sec = self.c["secondary"]
            for i in range(1, 4):
                angle = sec["ears"]["bounce"] * (1 - .16 * (i - 1)) * math.sin(2 * TAU * (phase - (sec["ears"]["delay_frames"] + i - 1) / n))
                for side in ("L", "R"):
                    self.key(f"ear_{i:02d}_{side}", f + 1, rotation=(angle, 0, 0))
            for i in range(1, 7):
                angle = sec["tail"]["follow_through"] * .45 * math.sin(TAU * (phase - (sec["tail"]["delay_frames"] + i - 1) / n))
                self.key(f"tail_{i:02d}", f + 1, rotation=(angle, 0, angle * .3))
        linear(action)
        end = round(self.s["duration_sec"] * self.s["fps"]) + 1
        self.strip(action, "Base cycle", 1, end=end, repeat=(end - 1) / n)
        # Two root keys only, regardless of scene length.
        root = bpy.data.actions.new(f"{self.id}::root_travel")
        ad.action = root
        direction = Vector((math.sin(FACING[self.c["facing"]]), -math.cos(FACING[self.c["facing"]]), 0))
        self.direction = direction
        for frame, sec in ((1, 0), (end, self.s["duration_sec"])):
            self.arm.location = Vector(self.c["position"]) + direction * a["root_speed"] * sec
            self.arm.keyframe_insert("location", frame=frame)
        linear(root)
        self.strip(root, "Root travel", 1, end=end)

    def gestures(self):
        for index, g in enumerate(self.c.get("gestures", [])):
            action = bpy.data.actions.new(f"{self.id}::gesture_{index}_{g['type']}")
            self.arm.animation_data.action = action
            duration = g["duration_sec"] * self.s["fps"]
            # Keys contain ONLY deltas. Zero at both ends; ADD NLA never replaces base.
            for i in range(33):
                u = i / 32
                fade = .25 if g["ease"] == "smooth" else .1
                w = smooth(u / fade) * smooth((1 - u) / fade) * g["intensity"]
                f = 1 + u * duration
                kind = g["type"]
                rot, loc = {}, {}
                if kind == "nod":
                    rot = {"head": (.3 * math.sin(TAU * u) * w, 0, 0), "neck": (.08 * math.sin(TAU * u) * w, 0, 0)}
                elif kind in ("head_turn", "look_around"):
                    turn = .55 * w * (math.sin(TAU * u) if kind == "look_around" else 1)
                    rot = {"head": (0, turn, 0), "neck": (0, turn * .25, 0)}
                elif kind in ("wave", "point"):
                    rot = {"clavicle_R": (0, 0, .08 * w), "upperarm_R": (-.8 * w, 0, (3.0 if kind == "wave" else 1.05) * w),
                           "lowerarm_R": ((.45 + (.32 * math.sin(6 * math.pi * u) if kind == "wave" else -.3)) * w, 0, 0),
                           "hand_R": (0, 0, .3 * math.sin(6 * math.pi * u) * w if kind == "wave" else 0)}
                elif kind == "crouch":
                    # Existing IK solves thigh/shin in response to lowered pelvis.
                    loc = {"pelvis": (0, 0, -.14 * w)}
                    rot = {"spine_01": (.1 * w, 0, 0), "spine_02": (.06 * w, 0, 0)}
                elif kind == "body_turn":
                    # The source CTRL_* controls are disconnected: pelvis is effective.
                    rot = {"pelvis": (0, .35 * w, 0)}
                elif kind == "ear_flick":
                    for j in range(1, 4):
                        for side in ("L", "R"):
                            rot[f"ear_{j:02d}_{side}"] = (.22 * math.sin(TAU * u - .3 * (j - 1)) * w, 0, 0)
                elif kind == "tail_flick":
                    for j in range(1, 7):
                        rot[f"tail_{j:02d}"] = (.12 * math.sin(TAU * u - .25 * j) * w, 0, .2 * math.sin(TAU * u - .25 * j) * w)
                for bone, v in rot.items():
                    self.key(bone, f, rotation=v)
                for bone, v in loc.items():
                    self.key(bone, f, translation=v)
            linear(action)
            start = 1 + g["start_sec"] * self.s["fps"]
            self.strip(action, f"Gesture {index}: {g['type']}", start, end=start + duration, additive=True)

    def face(self):
        expression = self.c["face"]["expression"]
        mouth, surprise = self.geo("mouth"), self.geo("surprise_mouth")
        mouth.hide_render = mouth.hide_viewport = expression == "surprised"
        surprise.hide_render = surprise.hide_viewport = expression != "surprised"
        surprise.scale = (1, 1, 1)
        if expression == "happy":
            keys = mouth.data.shape_keys
            if not keys or "smile" not in keys.key_blocks:
                fail(f"characters.{self.id}.face.expression", "source has no smile shape")
            keys.key_blocks["smile"].value = 1
        if expression == "surprised":
            for name, values in self.face_curves.items():
                if any(t in name for t in ("brow_", "eye_", "iris_")):
                    for path, idx, surprised, _ in values:
                        if path in ("location", "scale"):
                            getattr(self.objects[name], path)[idx] = surprised
        if self.c["face"]["blink"]:
            for side in ("L", "R"):
                lid = self.geo("lid_" + side)
                baseline = lid.location.copy()
                # Source lid arch travels .16 units. Repeat a 3-second blink action.
                for seconds, amount in ((0, 0), (1.1, 0), (1.18, -.16), (1.3, 0), (3, 0)):
                    lid.location = baseline + Vector((0, 0, amount))
                    lid.keyframe_insert("location", frame=1 + seconds * self.s["fps"])
                for fc in curves(lid.animation_data.action):
                    fc.modifiers.new("CYCLES")


def setup_scene(cfg, chars):
    sc = bpy.context.scene
    s = cfg["scene"]
    engines = sc.render.bl_rna.properties["engine"].enum_items.keys()
    sc.render.engine = "BLENDER_EEVEE" if "BLENDER_EEVEE" in engines else "BLENDER_EEVEE_NEXT"
    if hasattr(sc, "eevee"):
        if hasattr(sc.eevee, "taa_render_samples"):
            sc.eevee.taa_render_samples = s["samples"]
        elif hasattr(sc.eevee, "taa_samples"):
            sc.eevee.taa_samples = s["samples"]
    sc.render.resolution_x, sc.render.resolution_y = s["resolution"]
    sc.render.resolution_percentage = 100
    sc.render.fps = s["fps"]
    sc.render.fps_base = 1
    sc.frame_start, sc.frame_end = 1, round(s["duration_sec"] * s["fps"])
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGB"
    sc.render.film_transparent = False
    sc.render.use_file_extension = True
    sc.world = bpy.data.worlds.new("KIKO neutral studio")
    sc.world.use_nodes = True
    sc.world.node_tree.nodes["Background"].inputs[0].default_value = (.16, .18, .2, 1)
    sc.world.node_tree.nodes["Background"].inputs[1].default_value = .65
    if cfg["environment"]["ground"]:
        length = max(ch.c["action"]["root_speed"] * s["duration_sec"] + Vector(ch.c["position"]).length for ch in chars)
        bpy.ops.mesh.primitive_plane_add(size=2 * (length + 40))
        ground = bpy.context.object
        ground.name = "KIKO engine ground"
        material = bpy.data.materials.new("Neutral ground")
        material.diffuse_color = (.24, .27, .3, 1)
        material.use_nodes = True
        nt = material.node_tree
        bsdf = nt.nodes.get("Principled BSDF")
        bsdf.inputs["Roughness"].default_value = .85
        coords = nt.nodes.new("ShaderNodeTexCoord")
        checker = nt.nodes.new("ShaderNodeTexChecker")
        checker.inputs["Color1"].default_value = (.235, .255, .275, 1)
        checker.inputs["Color2"].default_value = (.255, .275, .295, 1)
        checker.inputs["Scale"].default_value = 1
        nt.links.new(coords.outputs["Object"], checker.inputs["Vector"])
        nt.links.new(checker.outputs["Color"], bsdf.inputs["Base Color"])
        ground.data.materials.append(material)
    # Sun lights maintain illumination along arbitrarily long travel paths.
    for name, energy, angles in (("Key", 2.2, (.45, -.6, -.5)), ("Fill", .8, (.6, .5, 2.4))):
        data = bpy.data.lights.new(name, "SUN")
        data.energy, data.angle = energy, .18
        obj = bpy.data.objects.new(name, data)
        sc.collection.objects.link(obj)
        obj.rotation_euler = angles
    c = cfg["camera"]
    target = next(ch for ch in chars if ch.id == c["target"])
    theta = FACING[target.c["facing"]]
    forward = target.direction
    right = Vector((math.cos(theta), math.sin(theta), 0))
    view = {"side": right, "front": forward, "3-4": (right + forward).normalized()}[c["angle"]]
    data = bpy.data.cameras.new("KIKO camera")
    cam = bpy.data.objects.new("KIKO camera", data)
    sc.collection.objects.link(cam)
    data.lens = 42
    sc.camera = cam
    aim = Vector(target.c["position"]) + Vector((0, 0, 1.6))
    offset = view * c["distance"] + Vector((0, 0, c["height"] - 1.6))
    cam.location = aim + offset
    cam.rotation_euler = (-offset).to_track_quat("-Z", "Y").to_euler()
    if c["type"] == "tracking":
        for f, t in ((1, 0), (sc.frame_end + 1, s["duration_sec"])):
            cam.location = aim + offset + forward * target.c["action"]["root_speed"] * t
            cam.keyframe_insert("location", frame=f)
        linear(cam.animation_data.action)
    sc.frame_set(1)
    return sc


def frame_at(f):
    whole = math.floor(f)
    bpy.context.scene.frame_set(whole, subframe=f - whole)
    bpy.context.view_layer.update()


def verify_motion(chars, sc):
    result = []
    for ch in chars:
        a, arm = ch.c["action"], ch.arm
        n, fps = a["loop_frames"], ch.s["fps"]
        max_slide, min_z, max_ik_error, min_bend, min_forward = 0., 1e6, 0., 180., 1e6
        max_contact_height = 0.
        previous = {}
        hips, arms, legs = [], [], []
        # Evaluate the final NLA stack and actual subdivided soles, at half frames.
        # For long shots also sample every gesture and the final cycle.
        sample_end = sc.frame_end - 1 if sc.frame_end <= 240 else min(sc.frame_end - 1, n * 2)
        samples = set(i / 2 + 1 for i in range(sample_end * 2 + 1))
        samples.update((max(1, sc.frame_end - n), sc.frame_end))
        for g in ch.c.get("gestures", []):
            samples.update(1 + fps * (g["start_sec"] + g["duration_sec"] * j / 32) for j in range(33))
        for f in sorted(samples):
            frame_at(f)
            hips.append(arm.pose.bones["pelvis"].head.x)
            arms.append(arm.pose.bones["hand_L"].head.y - arm.pose.bones["upperarm_L"].head.y)
            legs.append(arm.pose.bones["foot_L"].head.y - arm.pose.bones["thigh_L"].head.y)
            for side, off in (("L", 0), ("R", .5)):
                phase = ((f - 1) / n + off) % 1
                cycle = math.floor((f - 1) / n + off + 1e-8)
                planted = a["type"] == "idle" or phase < ch.stance - 1e-7
                foot = arm.pose.bones["foot_" + side]
                hip = arm.pose.bones["thigh_" + side].head
                knee = arm.pose.bones["shin_" + side].head
                ankle = arm.pose.bones["shin_" + side].tail
                target = arm.pose.bones["IK_foot_" + side].head
                max_ik_error = max(max_ik_error, (ankle - target).length)
                u, v = (hip - knee).normalized(), (ankle - knee).normalized()
                bend = 180 - math.degrees(math.acos(max(-1, min(1, u.dot(v)))))
                min_bend = min(min_bend, bend)
                segment = ankle - hip
                t = (knee - hip).dot(segment) / max(segment.length_squared, 1e-8)
                min_forward = min(min_forward, -(knee - (hip + segment * t)).y)
                points = mesh_points(ch.geo("foot_" + side))
                for i in range(3):
                    points += mesh_points(ch.geo(f"toe_{i}_{side}"))
                z = min(p.z for p in points)
                min_z = min(min_z, z)
                if planted:
                    max_contact_height = max(max_contact_height, abs(z - .003))
                prev = previous.get(side)
                if planted and prev and prev[0] == cycle and prev[1] and f - prev[2] <= .501:
                    # Every sole vertex must stay fixed, not just the IK target.
                    max_slide = max(max_slide, max((p - old).length for p, old in zip(points, prev[3])))
                previous[side] = (cycle, planted, f, points)
        # Loop positions and finite-difference velocities, without root travel.
        saved_mutes = [t.mute for t in arm.animation_data.nla_tracks]
        base_strip = next(t.strips[0] for t in arm.animation_data.nla_tracks if t.name == "Base cycle")
        saved_repeat, saved_end = base_strip.repeat, base_strip.frame_end
        base_strip.repeat = max(2, saved_repeat)
        for track in arm.animation_data.nla_tracks:
            if track.name.startswith("Gesture"):
                track.mute = True
        snapshots = []
        for f in (1, n + 1):
            frame_at(f)
            snapshots.append({pb.name: pb.matrix.copy() for pb in arm.pose.bones})
        loop_error = max(abs(snapshots[0][b][i][j] - snapshots[1][b][i][j]) for b in snapshots[0] for i in range(4) for j in range(4))
        for track, muted in zip(arm.animation_data.nla_tracks, saved_mutes):
            track.mute = muted
        base_strip.repeat, base_strip.frame_end = saved_repeat, saved_end
        def covariance(x, y):
            mx, my = sum(x) / len(x), sum(y) / len(y)
            numerator = sum((u - mx) * (v - my) for u, v in zip(x, y))
            denom = math.sqrt(sum((u - mx) ** 2 for u in x) * sum((v - my) ** 2 for v in y))
            return numerator / denom if denom else 0
        correlation = covariance(arms, legs)
        checks = {
            "rig_weights_and_deformation": {"pass": ch.audit["pass"]},
            "stance_no_sliding": {"pass": max_slide < .002, "max_vertex_displacement_per_half_frame": max_slide, "tolerance": .002},
            "no_foot_penetration": {"pass": min_z >= -.001, "min_evaluated_sole_z": min_z, "tolerance": -.001},
            "stance_ground_contact": {"pass": max_contact_height < .003, "max_height_error": max_contact_height, "tolerance": .003},
            "ik_reach": {"pass": max_ik_error < .002, "max_ankle_target_error": max_ik_error},
            "knees_forward": {"pass": min_forward > .005 and min_bend > 3, "min_forward_offset": min_forward, "min_bend_deg": min_bend},
            "pelvis_weight_transfer": {"pass": a["type"] == "idle" or max(hips) - min(hips) > .04, "lateral_range": max(hips) - min(hips)},
            "arms_oppose_legs": {"pass": a["type"] == "idle" or correlation < -.3, "hand_foot_forward_correlation": correlation},
            "loop_transition": {"pass": loop_error < 1e-4, "max_pose_matrix_difference": loop_error},
        }
        # Measure source secondary curves against the requested delayed waveform.
        base = next(t.strips[0].action for t in arm.animation_data.nla_tracks if t.name == "Base cycle")
        for kind, bone, amount, multiplier, harmonics in (("ears", "ear_01_L", "bounce", 1., 2), ("tail", "tail_01", "follow_through", .45, 1)):
            sec = ch.c["secondary"][kind]
            fc = next(fc for fc in curves(base) if fc.data_path == f'pose.bones["{bone}"].rotation_euler' and fc.array_index == 0)
            err = max(abs(fc.evaluate(1 + j) - sec[amount] * multiplier * math.sin(harmonics * TAU * (j - sec["delay_frames"]) / n)) for j in range(n))
            checks[kind + "_delayed_secondary"] = {"pass": err < 1e-5, "delay_frames": sec["delay_frames"], "max_waveform_error": err, "disabled": sec[amount] == 0}
        result.append({"id": ch.id, "checks": checks, "pass": all(v["pass"] for v in checks.values()), "sampled_frames": len(samples)})
    frame_at(1)
    return result


def gate_signature(cfg):
    h = hashlib.sha256(Path(__file__).read_bytes())
    h.update((ROOT / "KIKO_master_v1_1.blend").read_bytes())
    # Lighting/resolution/duration/gestures can change; base gait must match the gate.
    bases = [{k: c[k] for k in ("model", "armature", "action", "secondary")} for c in cfg["characters"]]
    h.update(json.dumps({"fps": cfg["scene"]["fps"], "bases": bases}, sort_keys=True).encode())
    return h.hexdigest()


def is_gate(cfg):
    s = cfg["scene"]
    return (s["duration_sec"] == 5 and s["fps"] == 24 and s["resolution"] == [854, 480]
            and cfg["camera"]["angle"] == "side" and cfg["environment"]["ground"]
            and all(c["action"]["type"] == "run" and not c.get("gestures") for c in cfg["characters"]))


def check_gate(cfg):
    if is_gate(cfg) or not any(c["action"]["type"] == "run" for c in cfg["characters"]):
        return
    gate = ROOT / "output" / "kiko_run_test_5s" / "verification.json"
    if gate.is_file():
        report = json.loads(gate.read_text())
        if report.get("status") == "PASS" and report.get("gate_signature") == gate_signature(cfg):
            return
    fail("gate", "render scenes/run_test_5s.json first; a matching PASS is required before other run renders (engine/model/base changes invalidate it)")


def prepare_frames(folder):
    # Never recurse-delete a user directory. Only clear engine-owned numbered PNGs.
    if folder.is_symlink():
        fail("output.frames", "refusing symlink frame directory")
    folder.mkdir(parents=True, exist_ok=True)
    marker = folder / ".kiko_engine_frames"
    entries = list(folder.iterdir())
    if entries and not marker.exists():
        fail("output.frames", f"{folder} is not an engine-owned directory; choose another output name")
    for p in entries:
        if p.name == marker.name:
            continue
        if not re.fullmatch(r"frame_\d{6}\.png", p.name) or not p.is_file() or p.is_symlink():
            fail("output.frames", f"unexpected file {p}; refusing cleanup")
    for p in entries:
        if p != marker:
            p.unlink()
    marker.write_text("Engine-owned rendered frames; safe to regenerate.\n")


def encode_command(cfg, frames, dest):
    return ["ffmpeg", "-y", "-framerate", str(cfg["scene"]["fps"]), "-start_number", "1",
            "-i", str(frames / "frame_%06d.png"), "-frames:v", str(round(cfg["scene"]["fps"] * cfg["scene"]["duration_sec"])),
            "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(dest)]


def contact_sheet(cfg, frames, work):
    s = cfg["scene"]
    requested = [0, .5, 1, 2, 3, 4, 5] if is_gate(cfg) else [s["duration_sec"] * i / 6 for i in range(7)]
    actual = [min(round(t * s["fps"]) + 1, round(s["duration_sec"] * s["fps"])) for t in requested]
    # Endpoint uses last encoded frame: 5s is exclusive, so label 4.958s explicitly.
    inputs, filters = [], []
    for i, (t, frame) in enumerate(zip(requested, actual)):
        inputs += ["-i", str(frames / f"frame_{frame:06d}.png")]
        filters.append(f"[{i}:v]scale=427:240[v{i}]")
    filters.append("".join(f"[v{i}]" for i in range(7)) + "xstack=inputs=7:layout=0_0|427_0|854_0|1281_0|0_240|427_240|854_240:fill=black[out]")
    cmd = [shutil.which("ffmpeg"), "-loglevel", "error", *inputs, "-filter_complex", ";".join(filters), "-map", "[out]", "-frames:v", "1", "-pix_fmt", "rgb24", "-f", "rawvideo", "pipe:1"]
    pixels = bytearray(subprocess.check_output(cmd))
    # Tiny built-in numeric font: FFmpeg builds without FreeType/drawtext work too.
    glyphs = {"0": "111101101101111", "1": "010110010010111", "2": "111001111100111",
              "3": "111001111001111", "4": "101101111001001", "5": "111100111001111",
              "6": "111100111101111", "7": "111001010010010", "8": "111101111101111",
              "9": "111101111001111", ".": "000000000000010", "s": "011100010001110",
              "f": "011010111010010", "|": "010010010010010", " ": "000000000000000"}
    width, height = 1708, 480
    if len(pixels) != width * height * 3:
        fail("output.contact_sheet", "unexpected raw image size")
    for tile, (t, frame) in enumerate(zip(requested, actual)):
        x0, y0 = (tile % 4) * 427 + 8, (tile // 4) * 240 + 8
        label = f"{t:.1f}s | f{frame} | {(frame - 1) / s['fps']:.3f}s"
        for y in range(y0 - 3, y0 + 18):
            start = (y * width + x0 - 3) * 3
            pixels[start:start + len(label) * 12 * 3 + 18] = bytes(len(label) * 12 * 3 + 18)
        for letter, char in enumerate(label):
            for cell, bit in enumerate(glyphs[char]):
                if bit == "1":
                    for dy in range(3):
                        start = ((y0 + (cell // 3) * 3 + dy) * width + x0 + letter * 12 + (cell % 3) * 3) * 3
                        pixels[start:start + 9] = bytes([255]) * 9
    subprocess.run([shutil.which("ffmpeg"), "-y", "-loglevel", "error", "-f", "rawvideo", "-pixel_format", "rgb24", "-video_size", f"{width}x{height}", "-i", "pipe:0", "-frames:v", "1", "-update", "1", str(work / "contact_sheet.jpg")], input=pixels, check=True)
    return [{"requested_sec": t, "frame": f, "actual_sec": (f - 1) / s["fps"]} for t, f in zip(requested, actual)]


def main():
    global REPORT_PATH
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scene_json", type=Path)
    parser.add_argument("--audit-only", action="store_true")
    parser.add_argument("--build-only", action="store_true")
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    args = parser.parse_args(argv)
    cfg = read_config(args.scene_json.resolve())
    dest = ROOT / cfg["output"]["mp4_path"]
    work = dest.with_suffix("")
    if work.is_symlink():
        fail("output.mp4_path", "artifact directory must not be a symlink")
    work.mkdir(parents=True, exist_ok=True)
    REPORT_PATH = work / "verification.json"
    frames = work / "frames"
    if not args.audit_only and not args.build_only:
        check_gate(cfg)
        if not shutil.which("ffmpeg"):
            print("FFmpeg is missing. After rendering the frames, encode with:\n" + shlex.join(encode_command(cfg, frames, dest)), flush=True)
            fail("output.ffmpeg", "ffmpeg must be installed/on PATH before rendering")
        if not shutil.which("ffprobe"):
            fail("output.ffprobe", "ffprobe must be installed/on PATH to verify encoded duration/fps/frame count")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    chars = []
    for c in cfg["characters"]:
        ch = Character(c, cfg["scene"])
        chars.append(ch)
        print(f"AUDIT {ch.id}: {len(ch.audit['repairs'])} targeted weight repairs; deformation={'PASS' if ch.audit['pass'] else 'FAIL'}", flush=True)
    dump(work / "rig_audit.json", [ch.audit for ch in chars])
    if not all(ch.audit["pass"] for ch in chars):
        fail("rig_audit", f"weight/deformation failure; see {work / 'rig_audit.json'}; rendering stopped")
    if args.audit_only:
        return
    for ch in chars:
        ch.base_action()
        ch.gestures()
        ch.face()
    sc = setup_scene(cfg, chars)
    motion = verify_motion(chars, sc)
    report = {"status": "BUILD_ONLY" if args.build_only else "RENDERING", "scene": str(args.scene_json),
              "gate_signature": gate_signature(cfg), "characters": motion,
              "requested": cfg["scene"], "visual_review": "pending contact-sheet inspection",
              "sampling": "evaluated mesh soles at half frames over two cycles, gesture windows and end of shot; not a proof for unsampled subframes"}
    for ch in motion:
        for name, check in ch["checks"].items():
            print(f"CHECK {ch['id']}.{name}: {'PASS' if check['pass'] else 'FAIL'} {json.dumps(check)}", flush=True)
    dump(work / "verification.json", report)
    if cfg["output"]["save_blend"]:
        bpy.ops.wm.save_as_mainfile(filepath=str(work / "scene.blend"))
    if args.build_only:
        return
    if not is_gate(cfg) and not all(ch["pass"] for ch in motion):
        report["status"] = "FAIL"
        dump(REPORT_PATH, report)
        fail("motion", "critical motion check failed before rendering; see verification.json")
    prepare_frames(frames)
    for f in range(1, sc.frame_end + 1):
        sc.frame_set(f)
        sc.render.filepath = str(frames / f"frame_{f:06d}.png")
        bpy.ops.render.render(write_still=True)
        if f % 12 == 0:
            print(f"RENDER {f}/{sc.frame_end}", flush=True)
    subprocess.run(encode_command(cfg, frames, dest), check=True)
    probe = json.loads(subprocess.check_output([shutil.which("ffprobe"), "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries", "stream=codec_name,pix_fmt,width,height,r_frame_rate,nb_read_frames,duration", "-of", "json", str(dest)], text=True))["streams"][0]
    s = cfg["scene"]
    report["video"] = probe
    report["video_pass"] = (probe["codec_name"] == "h264" and probe["pix_fmt"] == "yuv420p" and int(probe["nb_read_frames"]) == sc.frame_end and probe["r_frame_rate"] == f"{s['fps']}/1" and abs(float(probe["duration"]) - s["duration_sec"]) < 1e-4 and [probe["width"], probe["height"]] == s["resolution"])
    report["contact_sheet"] = contact_sheet(cfg, frames, work)
    report["status"] = "PASS" if report["video_pass"] and all(ch["pass"] for ch in motion) else "FAIL"
    dump(work / "verification.json", report)
    print(f"{report['status']}: {dest}\nVerification: {work / 'verification.json'}", flush=True)
    if report["status"] != "PASS":
        fail("gate", "critical check failed; stop. Inspect verification.json and repair the reported weight, IK, stride or timing problem before any longer render")


if __name__ == "__main__":
    try:
        import bpy
        from mathutils import Matrix, Vector
        main()
    except Exception as exc:
        print(f"KIKO ENGINE ERROR: {exc}", file=sys.stderr, flush=True)
        if REPORT_PATH is not None:
            try:
                report = json.loads(REPORT_PATH.read_text()) if REPORT_PATH.exists() else {}
                if report.get("status") != "FAIL":
                    report["status"] = "ERROR"
                report["error"] = str(exc)
                dump(REPORT_PATH, report)
            except Exception:
                traceback.print_exc()
        if not isinstance(exc, EngineError):
            traceback.print_exc()
        # Blender otherwise often exits zero after a Python exception. Flush and
        # explicitly terminate with failure so shell/CI callers can trust the code.
        sys.stdout.flush()
        sys.stderr.flush()
        import os
        os._exit(1)
