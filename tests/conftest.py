from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image


@pytest.fixture
def project_file(tmp_path: Path) -> Path:
    assets = tmp_path / "assets"; assets.mkdir()
    Image.new("RGBA", (64, 36), (20, 40, 60, 255)).save(assets / "bg.png")
    Image.new("RGBA", (12, 20), (200, 100, 80, 255)).save(assets / "person.png")
    data = {
        "format_version": 1,
        "project": {"title": "Test", "mode": "2.5d", "resolution": {"width": 64, "height": 36}, "fps": 5, "seed": 7, "timing_mode": "scenes_driven"},
        "scenes": [{"id": "one", "duration": 1.0, "background": {"source": "assets/bg.png"}, "layers": [{"id": "person", "source": "assets/person.png", "type": "character", "position": {"x": 0.5, "y": 0.5}}]}],
    }
    target = tmp_path / "story.json"; target.write_text(json.dumps(data), encoding="utf-8")
    return target

