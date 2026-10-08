"""JSON contract tests; no Blender import or rendering required."""
import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("kiko_engine", ROOT / "kiko_engine.py")
engine = importlib.util.module_from_spec(spec)
spec.loader.exec_module(engine)


class JsonContract(unittest.TestCase):
    def setUp(self):
        self.cfg = json.loads((ROOT / "scenes/run_test_5s.json").read_text())

    def invalid(self, cfg, field):
        with self.assertRaisesRegex(engine.EngineError, field):
            engine.validate(cfg)

    def test_examples_and_optional_empty_gestures(self):
        for path in (ROOT / "scenes").glob("run*.json"):
            engine.read_config(path)
        self.cfg["characters"][0]["gestures"] = []
        engine.validate(self.cfg)

    def test_missing_and_unknown_fields(self):
        del self.cfg["scene"]["samples"]
        self.invalid(self.cfg, "scene.samples")
        self.setUp()
        self.cfg["characters"][0]["face"]["viseme"] = "A"
        self.invalid(self.cfg, "face.viseme")

    def test_numeric_types_finiteness_and_pixel_format(self):
        for value in (True, "24", float("nan"), float("inf"), 24.0):
            c = copy.deepcopy(self.cfg)
            c["scene"]["fps"] = value
            self.invalid(c, "scene.fps")
        self.cfg["scene"]["resolution"] = [853, 480]
        self.invalid(self.cfg, "scene.resolution")

    def test_motion_constraints(self):
        self.cfg["characters"][0]["action"]["root_speed"] = 2
        self.invalid(self.cfg, "root_speed.*foot sliding")
        self.setUp()
        self.cfg["characters"][0]["position"][2] = 1
        self.invalid(self.cfg, "position")
        self.setUp()
        self.cfg["scene"]["duration_sec"] = 5.01
        self.invalid(self.cfg, "duration_sec.*integer frame")

    def test_gesture_types_and_bounds(self):
        g = {"type": "nod", "start_sec": 2, "duration_sec": .8, "intensity": .6, "ease": "smooth"}
        self.cfg["characters"][0]["gestures"] = [g]
        for kind in engine.GESTURES:
            g["type"] = kind
            engine.validate(self.cfg)
        g["type"] = "lip_sync"
        self.invalid(self.cfg, "supported values: nod, head_turn")
        g["type"], g["start_sec"] = "nod", 4.5
        self.invalid(self.cfg, "gesture ends after")

    def test_paths_and_character_identity(self):
        for dest in ("/tmp/movie.mp4", "output/../source.mp4", "output/a.mov", "source.mp4"):
            c = copy.deepcopy(self.cfg)
            c["output"]["mp4_path"] = dest
            self.invalid(c, "output.mp4_path")
        self.cfg["characters"].append(copy.deepcopy(self.cfg["characters"][0]))
        self.invalid(self.cfg, "duplicate character id")
        self.cfg["characters"][1]["id"] = "second"
        engine.validate(self.cfg)
        self.cfg["camera"]["target"] = "missing"
        self.invalid(self.cfg, "camera.target")

    def test_strict_json_and_owned_cleanup(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "bad.json"
            p.write_text('{"scene": 1, "scene": 2}')
            with self.assertRaisesRegex(engine.EngineError, "duplicate field"):
                engine.read_config(p)
            frames = Path(d) / "frames"
            frames.mkdir()
            precious = frames / "frame_000001.png"
            precious.write_bytes(b"user file")
            with self.assertRaisesRegex(engine.EngineError, "not an engine-owned"):
                engine.prepare_frames(frames)
            self.assertEqual(precious.read_bytes(), b"user file")
            precious.unlink()
            engine.prepare_frames(frames)
            precious.write_bytes(b"generated")
            engine.prepare_frames(frames)
            self.assertFalse(precious.exists())


if __name__ == "__main__":
    unittest.main()
