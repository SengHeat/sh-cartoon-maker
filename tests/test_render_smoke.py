from __future__ import annotations

import json

from PIL import Image

from cartoon_studio.config import load_project
from cartoon_studio.engine.director import Director


def _centroid_x(image: Image.Image, channel: int) -> float:
    pixels = image.convert("RGB")
    xs = [x for y in range(pixels.height) for x in range(pixels.width)
          if pixels.getpixel((x, y))[channel] > 200 and max(pixels.getpixel((x, y))[(channel + 1) % 3], pixels.getpixel((x, y))[(channel + 2) % 3]) < 60]
    assert xs
    return sum(xs) / len(xs)


def test_numbered_frames_show_depth_dependent_parallax(tmp_path, monkeypatch):
    assets = tmp_path / "assets"; assets.mkdir()
    Image.new("RGB", (96, 54), "#202020").save(assets / "bg.png")
    Image.new("RGBA", (8, 8), (255, 0, 0, 255)).save(assets / "far.png")
    Image.new("RGBA", (8, 8), (0, 0, 255, 255)).save(assets / "near.png")
    data = {
        "format_version": 1,
        "project": {"title": "Parallax proof", "mode": "2.5d", "resolution": {"width": 96, "height": 54}, "fps": 4, "seed": 1},
        "scenes": [{
            "id": "proof", "duration": 1, "background": {"source": "assets/bg.png", "scale": "cover"},
            "camera": {"movement": "pan_right"},
            "layers": [
                {"id": "far", "source": "assets/far.png", "depth": 0.15, "position": {"x": 0.5, "y": 0.35}},
                {"id": "near", "source": "assets/near.png", "depth": 0.9, "position": {"x": 0.5, "y": 0.65}},
            ],
        }],
    }
    story = tmp_path / "story.json"; story.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setenv("CARTOON_STUDIO_OUTPUT", str(tmp_path / "out"))
    result = Director().render(load_project(story), workers=1, force=True, dedupe=False)
    paths = sorted(result.frames_dir.glob("frame_*.png"))
    assert [path.name for path in paths] == [f"frame_{index:06d}.png" for index in range(1, 5)]
    first, last = Image.open(paths[0]), Image.open(paths[-1])
    far_shift = _centroid_x(last, 0) - _centroid_x(first, 0)
    near_shift = _centroid_x(last, 2) - _centroid_x(first, 2)
    assert abs(near_shift) > abs(far_shift) > 0
