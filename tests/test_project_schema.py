from __future__ import annotations

import json
import wave

import pytest

from cartoon_studio.config import AssetNotFoundError, ProjectError, TimingError, load_project
from cartoon_studio.models import Project


def test_valid_and_schema(project_file):
    assert load_project(project_file).duration == 1
    assert "properties" in Project.model_json_schema()


@pytest.mark.parametrize(("path", "value"), [("project.fps", 0), ("scenes.0.duration", -1), ("scenes.0.layers.0.position.x", 1.2)])
def test_invalid_values(project_file, path, value):
    data = json.loads(project_file.read_text())
    cursor = data
    parts = path.split(".")
    for part in parts[:-1]: cursor = cursor[int(part)] if part.isdigit() else cursor[part]
    cursor[parts[-1]] = value
    project_file.write_text(json.dumps(data))
    with pytest.raises(ProjectError): load_project(project_file)


def test_duplicate_scene(project_file):
    data = json.loads(project_file.read_text()); data["scenes"].append(data["scenes"][0])
    project_file.write_text(json.dumps(data))
    with pytest.raises(ProjectError, match="Duplicate scene"): load_project(project_file)


def test_missing_asset(project_file):
    data = json.loads(project_file.read_text()); data["scenes"][0]["background"]["source"] = "no.png"
    project_file.write_text(json.dumps(data))
    with pytest.raises(AssetNotFoundError, match="missing asset"): load_project(project_file)


def test_narration_driven_reconciles_scene_hints(project_file):
    narration = project_file.parent / "assets/narration.wav"
    with wave.open(str(narration), "wb") as stream:
        stream.setparams((1, 2, 8000, 16000, "NONE", "none")); stream.writeframes(b"\0\0" * 16000)
    data = json.loads(project_file.read_text()); data["audio"] = {"narration": "assets/narration.wav"}
    data["project"]["timing_mode"] = "narration_driven"
    project_file.write_text(json.dumps(data))
    loaded = load_project(project_file)
    assert loaded.duration == 2
    assert loaded.scene_durations == (2,)


def test_scenes_driven_rejects_long_narration(project_file):
    narration = project_file.parent / "assets/narration.wav"
    with wave.open(str(narration), "wb") as stream:
        stream.setparams((1, 2, 8000, 16000, "NONE", "none")); stream.writeframes(b"\0\0" * 16000)
    data = json.loads(project_file.read_text()); data["audio"] = {"narration": "assets/narration.wav"}
    project_file.write_text(json.dumps(data))
    with pytest.raises(TimingError, match="narration=2.000s, scenes=1.000s, delta=1.000s"):
        load_project(project_file)
