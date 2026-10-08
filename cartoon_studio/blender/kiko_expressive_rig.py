"""Additive V2 engineering rig; run in Blender after the Stage 2 gate passes.

This extends the technical V1.1 shell, not the rejected visual sculpt.
blender --background --python-exit-code 1 --python cartoon_studio/blender/kiko_expressive_rig.py
"""
from __future__ import annotations

import copy
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "cartoon_studio/blender"))
import kiko_master_plan as plan

e = plan.engine
REVIEW = ROOT / "review/kiko_v2_rig"
OUT = ROOT / "output/kiko_v2_rig_test"
VISEMES = ("VIS_REST", "VIS_AA", "VIS_EE", "VIS_IH", "VIS_OH", "VIS_OO", "VIS_MBP", "VIS_FV", "VIS_L")
BODY_POSES = ("neutral", "confident", "scared", "angry", "curious", "surprised", "happy", "sad", "crouch", "point", "wave")
FACE_POSES = ("neutral", "happy", "surprised", "angry", "sad", "curious", "scared")
CONTROLS = {"CTRL_pelvis": "pelvis", "CTRL_chest": "chest", "CTRL_jaw": "jaw",
            "CTRL_tail_base": "tail_01", "CTRL_tail_tip": "tail_06"}
for side in ("L", "R"):
    CONTROLS.update({f"CTRL_shoulder_{side}": f"clavicle_{side}", f"CTRL_hand_{side}": f"hand_{side}", f"CTRL_ear_{side}": f"ear_01_{side}"})


def prop(bone, name, minimum=0., maximum=1.):
    bone[name] = 0.
    bone.id_properties_ui(name).update(min=minimum, max=maximum, soft_min=minimum, soft_max=maximum)


def driver(owner, path, arm, bone, name, expression="v", index=None):
    curve = owner.driver_add(path) if index is None else owner.driver_add(path, index)
    d = curve.driver
    d.type = "SCRIPTED"
    d.expression = expression
    v = d.variables.new()
    v.name, v.type = "v", "SINGLE_PROP"
    v.targets[0].id = arm
    v.targets[0].data_path = f'pose.bones["{bone}"]["{name}"]'


def bind(obj, arm, bone):
    world = obj.matrix_world.copy()
    obj.parent, obj.parent_type = arm, "OBJECT"
    obj.matrix_world = world
    obj.vertex_groups.clear()
    vg = obj.vertex_groups.new(name=bone)
    vg.add(list(range(len(obj.data.vertices))), 1., "REPLACE")
    mod = next((m for m in obj.modifiers if m.type == "ARMATURE"), None)
    if mod is None:
        mod = obj.modifiers.new("V2 deformation", "ARMATURE")
    mod.object = arm


def add_controls(ch):
    arm = ch.arm
    bpy.context.view_layer.objects.active = arm
    arm.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    for name, target in CONTROLS.items():
        src = arm.data.edit_bones[target]
        b = arm.data.edit_bones.new(name)
        b.head, b.tail, b.roll = src.head, src.tail, src.roll
        b.parent, b.use_deform = src.parent, False
    for name, xyz in {"mouth_corner_L": (.16, -.65, 2.01), "mouth_corner_R": (-.16, -.65, 2.01),
                      "lip_upper": (0, -.65, 2.03), "lip_lower": (0, -.65, 1.96),
                      "CTRL_face": (0, -.8, 2.5), "CTRL_eye_aim": (0, -4, 2.3)}.items():
        b = arm.data.edit_bones.new(name)
        b.head, b.tail = xyz, Vector(xyz) + Vector((0, 0, .07))
        b.parent, b.use_deform = arm.data.edit_bones["head"], False
    # Previously unused finger chains were offset from the visible digits. Refit
    # only these dormant chains before skinning; preserve names and body chains.
    for side in ("L", "R"):
        for i in range(4):
            obj = ch.geo(f"digit_{i}_{side}")
            points = [obj.matrix_world @ v.co for v in obj.data.vertices]
            center = sum(points, Vector()) / len(points)
            b = arm.data.edit_bones[f"finger_{i:02d}_01_{side}"]
            b.head, b.tail = center + Vector((0, .065, 0)), center
            tip = arm.data.edit_bones[f"finger_{i:02d}_02_{side}"]
            tip.head, tip.tail = center, center + Vector((0, -.06, 0))
    bpy.ops.object.mode_set(mode="OBJECT")
    for name, target in CONTROLS.items():
        pb = arm.pose.bones[name]
        pb.rotation_mode = "XYZ"
        con = arm.pose.bones[target].constraints.new("COPY_ROTATION")
        con.name = "V2 additive " + name
        con.target, con.subtarget = arm, name
        con.owner_space = con.target_space = "LOCAL"
        con.mix_mode = "AFTER"
    prop(arm.pose.bones["CTRL_jaw"], "open")
    driver(arm.pose.bones["CTRL_jaw"], "rotation_euler", arm, "CTRL_jaw", "open", "0.32*v", 0)
    face = arm.pose.bones["CTRL_face"]
    for name in ("smile", "frown", "wide", "blink", "squint", "brow_angry", "brow_sad", *VISEMES):
        prop(face, name)
    for name in ("mouth_corner_L", "mouth_corner_R", "lip_upper", "lip_lower"):
        prop(arm.pose.bones[name], "offset", -1, 1)
    for side in ("L", "R"):
        eye = arm.pose.bones["eye_" + side]
        con = eye.constraints.new("DAMPED_TRACK")
        con.name = "V2 gaze follows head-relative target"
        con.target, con.subtarget, con.track_axis = arm, "CTRL_eye_aim", "TRACK_Y"
        for part in ("iris_", "pupil_"):
            bind(ch.geo(part + side), arm, "eye_" + side)
        for i in range(4):
            bind(ch.geo(f"digit_{i}_{side}"), arm, f"finger_{i:02d}_01_{side}")


def eyelid(ch, side):
    """A skin surface that covers the eyeball, with actual closed geometry."""
    arm = ch.arm
    eye = ch.geo("eye_" + side)
    points = [eye.matrix_world @ v.co for v in eye.data.vertices]
    lo = Vector(tuple(min(p[i] for p in points) for i in range(3)))
    hi = Vector(tuple(max(p[i] for p in points) for i in range(3)))
    center = (lo + hi) / 2
    radii = (hi - lo) / 2 + Vector((.009, .04, .01))
    rings, segments = 16, 32

    def coords(extent):
        result = []
        for i in range(rings + 1):
            theta = .001 + (extent - .001) * i / rings
            for j in range(segments):
                phi = math.tau * j / segments
                result.append(center + Vector((radii.x * math.sin(theta) * math.cos(phi),
                                               radii.y * math.sin(theta) * math.sin(phi), radii.z * math.cos(theta))))
        return result

    faces = []
    for i in range(rings):
        for j in range(segments):
            a = i * segments + j
            b = i * segments + (j + 1) % segments
            faces.append((a, a + segments, b + segments, b))
    mesh = bpy.data.meshes.new("V2 eyelid " + side)
    mesh.from_pydata(coords(.65), [], faces)
    mesh.update()
    obj = bpy.data.objects.new("KIKO_GEO_eyelid_surface_" + side, mesh)
    bpy.context.collection.objects.link(obj)
    mesh.materials.append(bpy.data.materials.get("fur_gray"))
    for poly in mesh.polygons:
        poly.use_smooth = True
    obj.shape_key_add(name="Basis")
    for name, extent in (("blink", math.pi - .001), ("squint", 1.55)):
        key = obj.shape_key_add(name=name)
        for v, co in zip(key.data, coords(extent)):
            v.co = co
        driver(key, "value", arm, "CTRL_face", name)
    bind(obj, arm, "head")
    ch.geo("lid_" + side).hide_render = True
    ch.geo("lid_" + side).hide_viewport = True
    ch.objects[obj.name] = obj


def facial_mesh(ch):
    arm = ch.arm
    # Source showcase's open-mouth object has sufficient topology for a technical
    # lip/viseme patch. Preserve the original mouth and its legacy expression keys.
    source = ch.geo("surprise_mouth")
    obj = source.copy()
    obj.data = source.data.copy()
    obj.name = "KIKO_GEO_v2_mouth"
    bpy.context.collection.objects.link(obj)
    obj.animation_data_clear()
    obj.parent = None
    obj.matrix_world = Matrix.Identity(4)
    obj.hide_render = obj.hide_viewport = False
    points = [v.co.copy() for v in obj.data.vertices]
    lo = Vector(tuple(min(p[i] for p in points) for i in range(3)))
    hi = Vector(tuple(max(p[i] for p in points) for i in range(3)))
    center, radius = (hi + lo) / 2, (hi - lo) / 2
    normalized = [Vector(tuple((p[i] - center[i]) / max(radius[i], 1e-6) for i in range(3))) for p in points]
    for v, p in zip(obj.data.vertices, normalized):
        v.co = (p.x * .15, -.650 + p.y * .012, 2.005 + p.z * .009)
    basis = obj.shape_key_add(name="Basis")

    def key(name, width=.15, opening=.018, smile=0., forward=0.):
        shape = obj.shape_key_add(name=name)
        for v, p in zip(shape.data, normalized):
            v.co = (p.x * width, -.650 + p.y * .012 - forward,
                    2.014 - opening / 2 + p.z * opening / 2 + smile * p.x ** 2)
        return shape

    # AA is also the jaw opening baseline. Expressions and visemes remain separate
    # so the acting layer can coexist with future speech curves.
    for name, width, opening in (("VIS_REST", .15, .018), ("VIS_AA", .14, .16),
                                 ("VIS_EE", .19, .055), ("VIS_IH", .15, .06),
                                 ("VIS_OH", .085, .13), ("VIS_OO", .055, .07),
                                 ("VIS_MBP", .145, .004), ("VIS_FV", .135, .024), ("VIS_L", .14, .085)):
        k = key(name, width, opening)
        driver(k, "value", arm, "CTRL_face", name)
    k = key("jaw_open", .15, .18)
    driver(k, "value", arm, "CTRL_jaw", "open")
    for name, width, smile in (("smile", .18, .05), ("frown", .15, -.04), ("wide", .21, .04)):
        k = key(name, width, .018, smile)
        driver(k, "value", arm, "CTRL_face", name)
    for name in ("mouth_corner_L", "mouth_corner_R", "lip_upper", "lip_lower"):
        k = obj.shape_key_add(name=name)
        k.slider_min = -1
        for v, base, p in zip(k.data, basis.data, normalized):
            v.co = base.co.copy()
            weight = max(0, p.x) ** 2 if name.endswith("L") else max(0, -p.x) ** 2 if name.endswith("R") else max(0, p.z) if name == "lip_upper" else max(0, -p.z)
            v.co.z += .04 * weight
        driver(k, "value", arm, name, "offset")
    bind(obj, arm, "head")
    # The source open-mouth oval floats ahead of the muzzle. Project the final
    # deformed mouth surface onto the final deformed muzzle, after the armature.
    wrap = obj.modifiers.new("V2 attached mouth surface", "SHRINKWRAP")
    wrap.target = ch.geo("muzzle")
    wrap.wrap_method = "NEAREST_SURFACEPOINT"
    wrap.wrap_mode = "ABOVE_SURFACE"
    wrap.offset = .0015
    matte = bpy.data.materials.new("V2 mouth interior matte")
    matte.use_nodes = True
    bsdf = matte.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (.018, .002, .003, 1)
    bsdf.inputs["Roughness"].default_value = 1
    bsdf.inputs["Specular IOR Level"].default_value = 0
    obj.data.materials.clear()
    obj.data.materials.append(matte)
    ch.objects[obj.name] = obj
    for short in ("mouth", "surprise_mouth", "tongue"):
        ch.geo(short).hide_render = ch.geo(short).hide_viewport = True
    muzzle = ch.geo("muzzle")
    for v in muzzle.data.vertices:
        weight = .8 * (1 - e.smooth((v.co.z - 1.86) / .20))
        e.set_weight(muzzle, v.index, {"head": 1 - weight, "jaw": weight})
    for side, sign in (("L", 1), ("R", -1)):
        original = ch.geo("brow_" + side)
        evaluated = original.evaluated_get(bpy.context.evaluated_depsgraph_get())
        mesh = bpy.data.meshes.new_from_object(evaluated)
        mesh.transform(original.matrix_world)
        brow = bpy.data.objects.new("KIKO_GEO_v2_brow_" + side, mesh)
        bpy.context.collection.objects.link(brow)
        brow.shape_key_add(name="Basis")
        for expression, slope in (("brow_angry", .32), ("brow_sad", -.32)):
            shape = brow.shape_key_add(name=expression)
            for v in shape.data:
                v.co.z += slope * (abs(v.co.x) - .2)
            driver(shape, "value", arm, "CTRL_face", expression)
        bind(brow, arm, "head")
        original.hide_render = original.hide_viewport = True
        ch.objects[brow.name] = brow
    return obj


def reset(ch):
    # Keep rig drivers when switching pose/actions. animation_data_clear() would
    # silently disconnect the jaw control as well as removing the test timeline.
    ad = ch.arm.animation_data
    if ad:
        ad.action = None
        for track in list(ad.nla_tracks):
            ad.nla_tracks.remove(track)
    ch.arm.location = (0, 0, 0)
    ch.arm.rotation_euler = (0, 0, 0)
    for pb in ch.arm.pose.bones:
        pb.rotation_mode = "XYZ"
        pb.matrix_basis = Matrix.Identity(4)
        for key in pb.keys():
            if isinstance(pb[key], (int, float)):
                pb[key] = 0.
    # Supported flat-ground neutral, inherited from the existing IK solver.
    ch.arm.pose.bones["pelvis"].location = e.bone_location(ch.arm.pose.bones["pelvis"], (0, 0, -.13))
    for side in ("L", "R"):
        pb = ch.arm.pose.bones["IK_foot_" + side]
        ankle = ch.arm.data.bones["foot_" + side].head_local.copy()
        ankle.z += .003 - ch.sole_z[side]
        pb.location = e.bone_location(pb, ankle - pb.bone.head_local)
    ch.arm.update_tag()
    bpy.context.view_layer.update()


def pose(ch, name, body=True):
    reset(ch)
    b = ch.arm.pose.bones
    face = b["CTRL_face"]
    if name in ("happy", "smile", "wave"):
        face["smile"] = .85
        b["CTRL_ear_L"].rotation_euler.x = -.15
        b["CTRL_ear_R"].rotation_euler.x = -.15
        b["CTRL_tail_base"].rotation_euler.z = .18
    if name in ("mouth_open", "surprised", "scared"):
        b["CTRL_jaw"]["open"] = .8 if name != "scared" else .45
        b["CTRL_ear_L"].rotation_euler.x = -.22 if name != "scared" else .65
        b["CTRL_ear_R"].rotation_euler.x = -.22 if name != "scared" else .65
    if name in ("sad", "angry"):
        face["frown"] = .9
        face["squint"] = .25 if name == "sad" else .65
        face["brow_angry"] = .8 if name == "angry" else 0
        face["brow_sad"] = .9 if name == "sad" else 0
        b["head"].rotation_euler.x = .15 if name == "sad" else .05
    if name == "curious":
        b["head"].rotation_euler.y = -.18
        b["CTRL_ear_L"].rotation_euler.x = -.3
        b["CTRL_ear_R"].rotation_euler.x = .25
        b["CTRL_eye_aim"].location.x = .35
        face["smile"] = .25
    if name == "blink":
        face["blink"] = 1
    if body and name in ("crouch", "scared"):
        b["pelvis"].location = e.bone_location(b["pelvis"], (0, 0, -.29))
        b["spine_01"].rotation_euler.x = .15
        b["head"].rotation_euler.x = -.12
        b["CTRL_tail_base"].rotation_euler.x = -.35
    if body and name == "wave":
        b["upperarm_R"].rotation_euler = (-.64, 0, 2.4)
        b["lowerarm_R"].rotation_euler = (.4, 0, 0)
        b["CTRL_hand_R"].rotation_euler.x = -.25
    if body and name == "happy":
        for side, sign in (("L", -1), ("R", 1)):
            b["upperarm_" + side].rotation_euler = (0, 0, sign * 2.05)
            b["lowerarm_" + side].rotation_euler.x = .15
        b["head"].rotation_euler.x = -.08
        b["CTRL_jaw"]["open"] = .15
        face["wide"] = .35
    if body and name == "point":
        b["upperarm_R"].rotation_euler = (-.2, 0, 1.5)
        b["lowerarm_R"].rotation_euler.x = .1
        b["chest"].rotation_euler.y = -.12
        b["head"].rotation_euler.y = -.18
        for i in (1, 2, 3):
            b[f"finger_{i:02d}_01_R"].rotation_euler.x = .6
    if body and name == "confident":
        b["chest"].rotation_euler.x = -.08
        b["head"].rotation_euler.x = -.06
        face["smile"] = .35
    ch.arm.update_tag()
    bpy.context.view_layer.update()


def save_pose(ch, name):
    action = bpy.data.actions.new(name)
    ch.arm.animation_data_create().action = action
    for pb in ch.arm.pose.bones:
        for path in ("location", "rotation_euler", "scale"):
            pb.keyframe_insert(path, frame=1, group=pb.name)
        for key in pb.keys():
            if isinstance(pb[key], (int, float)):
                pb.keyframe_insert(f'["{key}"]', frame=1, group=pb.name)
    action.use_fake_user = True
    action.asset_mark()
    action.asset_data.description = "KIKO V2 reusable engineering validation pose"
    ch.arm.animation_data.action = None


def secondary_library(ch):
    for name, curl in (("relaxed", .12), ("open", 0.), ("fist", .9), ("grip", .6), ("point", .8), ("wave", 0.)):
        pose(ch, "wave" if name == "wave" else "neutral")
        for side in ("L", "R"):
            for i in range(4):
                ch.arm.pose.bones[f"finger_{i:02d}_01_{side}"].rotation_euler.x = 0 if name == "point" and i == 0 else curl
                ch.arm.pose.bones[f"finger_{i:02d}_02_{side}"].rotation_euler.x = curl * .4
        save_pose(ch, "HAND_" + name)
    for name, left, right in (("neutral", 0, 0), ("alert", -.25, -.25), ("relaxed", .2, .2), ("frightened", .65, .65), ("asymmetric", -.3, .3)):
        reset(ch)
        ch.arm.pose.bones["CTRL_ear_L"].rotation_euler.x = left
        ch.arm.pose.bones["CTRL_ear_R"].rotation_euler.x = right
        save_pose(ch, "EAR_" + name)
    for name, bend, wag in (("relaxed", 0, 0), ("happy", .1, .25), ("scared", -.4, 0), ("alert", .25, 0), ("angry", .15, -.08)):
        reset(ch)
        ch.arm.pose.bones["CTRL_tail_base"].rotation_euler = (bend, 0, wag)
        ch.arm.pose.bones["CTRL_tail_tip"].rotation_euler.x = bend * .4
        save_pose(ch, "TAIL_" + name)


def functional_checks(ch):
    checks = {}
    def moved(label, mesh, bone, property_name, value):
        reset(ch)
        before = e.mesh_points(bpy.data.objects[mesh])
        ch.arm.pose.bones[bone][property_name] = value
        ch.arm.update_tag()
        bpy.context.view_layer.update()
        after = e.mesh_points(bpy.data.objects[mesh])
        displacement = max((a - b).length for a, b in zip(before, after))
        checks[label] = {"max_vertex_displacement": displacement, "pass": displacement > .0001}
    moved("jaw_deforms_muzzle", "KIKO_GEO_muzzle", "CTRL_jaw", "open", .8)
    moved("blink_surface_moves", "KIKO_GEO_eyelid_surface_L", "CTRL_face", "blink", 1.)
    for name in VISEMES:
        if name != "VIS_REST":
            moved(name, "KIKO_GEO_v2_mouth", "CTRL_face", name, 1.)
    for name in ("mouth_corner_L", "mouth_corner_R", "lip_upper", "lip_lower"):
        moved(name, "KIKO_GEO_v2_mouth", name, "offset", 1.)
    reset(ch)
    for side in ("L", "R"):
        obj = ch.geo("digit_0_" + side)
        before = e.mesh_points(obj)
        ch.arm.pose.bones["finger_00_01_" + side].rotation_euler.x = .6
        ch.arm.update_tag()
        bpy.context.view_layer.update()
        displacement = max((a - b).length for a, b in zip(before, e.mesh_points(obj)))
        checks["finger_binding_" + side] = {"max_vertex_displacement": displacement, "pass": displacement > .01}
    for angle in (0., .4, -.4):
        reset(ch)
        ch.arm.pose.bones["head"].rotation_euler.y = angle
        ch.arm.update_tag()
        bpy.context.view_layer.update()
        target = ch.arm.pose.bones["CTRL_eye_aim"].head
        for side in ("L", "R"):
            eye = ch.arm.pose.bones["eye_" + side]
            dot = (eye.tail - eye.head).normalized().dot((target - eye.head).normalized())
            checks[f"eye_aim_{side}_head_{angle}"] = {"aim_alignment": dot, "pass": dot > .999}
    reset(ch)
    return checks


def camera(scene, face=True):
    cam = scene.camera
    cam.animation_data_clear()
    cam.location = (.35, -4.5, 2.55) if face else (3.0, -7.5, 2.7)
    aim = Vector((0, -.1, 2.45 if face else 1.8))
    cam.rotation_euler = (aim - cam.location).to_track_quat("-Z", "Y").to_euler()
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = 3.2 if face else 6.8


def main():
    gate = json.loads((ROOT / "output/kiko_run_test_5s/verification.json").read_text())
    cfg = e.read_config(ROOT / "scenes/kiko_master_run_gate.json")
    if gate["status"] != "PASS" or gate["gate_signature"] != e.gate_signature(cfg):
        raise RuntimeError("Stage 2 must pass with the current engine and source")
    REVIEW.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    plan.backup([ROOT / "KIKO_master_v2.blend", OUT / "verification.json"])
    report = {"status": "BUILDING", "pass": False, "visual_review": "PENDING", "source_sha256": plan.digest(plan.SOURCE)}
    plan.dump(OUT / "verification.json", report)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    cfg["characters"][0]["facing"] = "south"
    ch = e.Character(cfg["characters"][0], cfg["scene"])
    ch.arm.rotation_euler = (0, 0, 0)
    for obj in ch.objects.values():
        obj.animation_data_clear()
    ch.arm.data.pose_position = "REST"
    bpy.context.view_layer.update()
    add_controls(ch)
    for side in ("L", "R"):
        eyelid(ch, side)
    mouth = facial_mesh(ch)
    ch.arm.data.pose_position = "POSE"
    # Reuse locomotion API after adding controls to measure actual compatibility.
    ch.base_action()
    scene = e.setup_scene(cfg, [ch])
    run = e.verify_motion([ch], scene)
    report["run_compatibility"] = run
    for track in ch.arm.animation_data.nla_tracks:
        for strip in track.strips:
            strip.action.use_fake_user = True
    reset(ch)
    ch.c = copy.deepcopy(ch.c)
    ch.c["action"].update(type="walk", stride_length=.8, root_speed=.96, pelvis_bounce=.03)
    ch.base_action()
    walk = e.verify_motion([ch], scene)
    report["walk_compatibility"] = walk
    reset(ch)
    # Keep original object names and body-bone API in the versioned master.
    for original, obj in ch.objects.items():
        if "::" in obj.name:
            obj.name = original
    for name in BODY_POSES:
        pose(ch, name)
        save_pose(ch, "POSE_" + name)
    for name in FACE_POSES:
        pose(ch, name, body=False)
        save_pose(ch, "FACE_" + name)
    secondary_library(ch)
    report["functional_checks"] = functional_checks(ch)
    pose(ch, "neutral")
    camera(scene, False)
    scene.frame_start, scene.frame_end = 1, 192
    for side in ("L", "R"):
        ch.arm["kiko_sole_z_" + side] = ch.sole_z[side]
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / "KIKO_master_v2.blend"))
    report["master_sha256"] = plan.digest(ROOT / "KIKO_master_v2.blend")
    renders = []
    for name in ("neutral", "smile", "mouth_open", "surprised", "angry", "sad", "curious", "scared", "wave_full_body", "crouch_full_body", "blink", "point_full_body", "happy_full_body"):
        pose(ch, name.replace("_full_body", ""))
        camera(scene, not name.endswith("full_body"))
        path = REVIEW / (name + ".png")
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        renders.append(str(path.relative_to(ROOT)))
    for name in ("open", "fist", "point", "grip"):
        reset(ch)
        ch.arm.animation_data_create().action = bpy.data.actions["HAND_" + name]
        scene.frame_set(1)
        bpy.context.view_layer.update()
        points = e.mesh_points(ch.geo("hand_R"))
        target = sum(points, Vector()) / len(points)
        cam = scene.camera
        cam.location = target + Vector((-.5, -2, .4))
        cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
        cam.data.ortho_scale = .9
        path = REVIEW / f"hand_{name}.png"
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        renders.append(str(path.relative_to(ROOT)))
    report.update(status="AWAITING_VISUAL_REVIEW", renders=renders,
                  visemes=list(mouth.data.shape_keys.key_blocks.keys()),
                  pose_actions=[a.name for a in bpy.data.actions if a.name.startswith(("POSE_", "FACE_"))],
                  controls=list(CONTROLS), source_unchanged=plan.digest(plan.SOURCE) == report["source_sha256"],
                  limitations=["Technical V1.1 shell only; no final visual likeness claim.",
                               "Mouth uses the source overlay topology; inspect carefully for surface detachment.",
                               "FV/L are approximate base openings; no teeth/tongue articulation yet.",
                               "Finger skinning uses existing discrete digit meshes; grip requires visual QA."])
    subprocess.run([shutil.which("python3") or "python3", "-m", "cartoon_studio.kiko_review_sheet", "--output",
                    str(REVIEW / "validation_contact_sheet.jpg"), *[str(ROOT / p) for p in renders]], cwd=ROOT, check=True)
    report["contact_sheet_path"] = "review/kiko_v2_rig/validation_contact_sheet.jpg"
    if not all(m["pass"] for m in run + walk) or not all(c["pass"] for c in report["functional_checks"].values()):
        report["status"] = "FAIL"
    plan.dump(OUT / "verification.json", report)
    if report["status"] == "FAIL":
        raise RuntimeError("V2 body compatibility or functional controls failed")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        path = OUT / "verification.json"
        report = json.loads(path.read_text()) if path.exists() else {}
        report.update(status="FAIL", **{"pass": False}, error=str(exc))
        plan.dump(path, report)
        raise
