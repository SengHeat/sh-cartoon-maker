"""Integration checks: blender --background --python tests/test_kiko_engine_blender.py"""
import copy
import importlib.util
import sys
import unittest
from pathlib import Path

try:
    import bpy
    from mathutils import Matrix, Vector
except ImportError:
    bpy = None

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipIf(bpy is None, "requires Blender Python")
class BlenderIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("kiko_engine", ROOT / "blender" / "kiko_engine.py")
        cls.e = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.e)
        cls.e.bpy, cls.e.Matrix, cls.e.Vector = bpy, Matrix, Vector
        cls.cfg = cls.e.read_config(ROOT / "blender/shots/run_with_gestures_demo.json")
        other = copy.deepcopy(cls.cfg["characters"][0])
        other.update(id="second", position=[4, 2, 0], facing="north", gestures=[])
        other["face"] = {"expression": "surprised", "blink": False}
        cls.cfg["characters"].append(other)
        bpy.ops.wm.read_factory_settings(use_empty=True)
        cls.chars = [cls.e.Character(c, cls.cfg["scene"]) for c in cls.cfg["characters"]]
        for ch in cls.chars:
            ch.base_action()
            ch.gestures()
            ch.face()
        cls.scene = cls.e.setup_scene(cls.cfg, cls.chars)

    def test_instances_do_not_share_rig_mesh_or_action_data(self):
        a, b = self.chars
        self.assertIsNot(a.arm.data, b.arm.data)
        self.assertIsNot(a.geo("mouth").data, b.geo("mouth").data)
        for ch in self.chars:
            for obj in ch.objects.values():
                for mod in obj.modifiers:
                    if mod.type == "ARMATURE":
                        self.assertEqual(mod.object, ch.arm)
                if obj != ch.arm:
                    self.assertEqual(obj.parent, ch.arm)
            for side in ("L", "R"):
                ik = next(c for c in ch.arm.pose.bones["shin_" + side].constraints if c.type == "IK")
                self.assertEqual(ik.target, ch.arm)
                self.assertEqual(ik.pole_target, ch.arm)
        a_actions = {s.action for t in a.arm.animation_data.nla_tracks for s in t.strips}
        b_actions = {s.action for t in b.arm.animation_data.nla_tracks for s in t.strips}
        self.assertFalse(a_actions & b_actions)

    def test_gesture_is_additive_and_returns_to_base(self):
        ch = self.chars[0]
        for index, bone, seconds in ((0, "head", 2.2), (1, "upperarm_R", 5.5)):
            track = next(t for t in ch.arm.animation_data.nla_tracks if t.name.startswith(f"Gesture {index}:"))
            strip = track.strips[0]
            self.assertEqual(strip.blend_type, "ADD")
            f = 1 + seconds * self.cfg["scene"]["fps"]
            self.e.frame_at(f)
            layered = ch.arm.pose.bones[bone].rotation_euler.copy()
            if bone == "upperarm_R":
                self.assertGreater(ch.arm.pose.bones["hand_R"].head.z,
                                   ch.arm.pose.bones["upperarm_R"].head.z + .1,
                                   "wave paw must rise visibly above the shoulder")
            track.mute = True
            self.e.frame_at(f)
            base = ch.arm.pose.bones[bone].rotation_euler.copy()
            track.mute = False
            source_frame = f - strip.frame_start + strip.action_frame_start
            expected = Vector((0, 0, 0))
            for fc in self.e.curves(strip.action):
                if fc.data_path == f'pose.bones["{bone}"].rotation_euler':
                    expected[fc.array_index] = fc.evaluate(source_frame)
            self.assertGreater(expected.length, .01)
            self.assertLess((Vector(layered) - Vector(base) - expected).length, 1e-5)
            for f in (strip.frame_start - .1, strip.frame_start, strip.frame_end, strip.frame_end + .1):
                self.e.frame_at(f)
                layered = ch.arm.pose.bones[bone].rotation_euler.copy()
                track.mute = True
                self.e.frame_at(f)
                base = ch.arm.pose.bones[bone].rotation_euler.copy()
                track.mute = False
                self.assertLess((Vector(layered) - Vector(base)).length, 1e-5)

    def test_faces_and_root_travel_are_independent(self):
        a, b = self.chars
        self.assertEqual(a.geo("mouth").data.shape_keys.key_blocks["smile"].value, 1)
        self.assertFalse(a.geo("mouth").hide_render)
        self.assertTrue(a.geo("surprise_mouth").hide_render)
        self.assertTrue(b.geo("mouth").hide_render)
        self.assertFalse(b.geo("surprise_mouth").hide_render)
        self.e.frame_at(25)
        for ch in self.chars:
            expected = Vector(ch.c["position"]) + ch.direction * ch.c["action"]["root_speed"]
            self.assertLess((ch.arm.location - expected).length, 1e-5)
            root = next(t.strips[0].action for t in ch.arm.animation_data.nla_tracks if t.name == "Root travel")
            self.assertTrue(all(len(fc.keyframe_points) == 2 for fc in self.e.curves(root)))

    def test_walk_idle_and_all_gesture_bone_maps(self):
        for kind, stride in (("walk", .8), ("idle", 0)):
            cfg = copy.deepcopy(self.cfg)
            cfg["scene"]["duration_sec"] = 5
            cfg["characters"] = [copy.deepcopy(cfg["characters"][0])]
            c = cfg["characters"][0]
            c.update(id="diagnostic_" + kind, gestures=[])
            c["action"].update(type=kind, stride_length=stride, root_speed=stride * 24 / 28, pelvis_bounce=.03)
            cfg["camera"]["target"] = c["id"]
            self.e.validate(cfg)
            ch = self.e.Character(c, cfg["scene"])
            ch.base_action()
            ch.face()
            sc = self.e.setup_scene(cfg, [ch])
            measured = self.e.verify_motion([ch], sc)[0]
            self.assertTrue(measured["pass"], measured)
        # Exercise all advertised gesture maps on the idle character, checking
        # successful action creation and zero deltas at both timeline boundaries.
        ch.c["gestures"] = [{"type": kind, "start_sec": 1, "duration_sec": 1,
                              "intensity": .6, "ease": "sharp"} for kind in self.e.GESTURES]
        ch.gestures()
        tracks = [t for t in ch.arm.animation_data.nla_tracks if t.name.startswith("Gesture")]
        self.assertEqual(len(tracks), len(self.e.GESTURES))
        for t in tracks:
            strip = t.strips[0]
            self.assertEqual(strip.blend_type, "ADD")
            fcurves = list(self.e.curves(strip.action))
            self.assertTrue(fcurves)
            self.assertTrue(any(abs(k.co.y) > .01 for fc in fcurves for k in fc.keyframe_points))
            for fc in fcurves:
                self.assertAlmostEqual(fc.evaluate(strip.action_frame_start), 0, places=6)
                self.assertAlmostEqual(fc.evaluate(strip.action_frame_end), 0, places=6)

    def test_run_rises_in_flight_without_losing_planted_feet(self):
        cfg = self.e.read_config(ROOT / "scenes/kiko_master_run_gate.json")
        ch = self.e.Character(cfg["characters"][0], cfg["scene"])
        ch.base_action()
        sc = self.e.setup_scene(cfg, [ch])
        # Compare the evaluated body in compressed stance and mid-flight. The
        # former waveform peaked during stance and could pass the old checks.
        n = ch.c["action"]["loop_frames"]
        self.e.frame_at(1 + n * .18)
        compressed = ch.arm.pose.bones["pelvis"].head.z
        self.e.frame_at(1 + n * .43)
        airborne = ch.arm.pose.bones["pelvis"].head.z
        self.assertGreater(airborne - compressed, .07)
        measured = self.e.verify_motion([ch], sc)[0]
        self.assertTrue(measured["pass"], measured)
        self.assertGreater(measured["checks"]["knees_forward"]["min_bend_deg"], 20)


if __name__ == "__main__":
    result = unittest.main(argv=[sys.argv[0]], exit=False, verbosity=2).result
    if not result.wasSuccessful():
        sys.stdout.flush()
        sys.stderr.flush()
        import os
        os._exit(1)
