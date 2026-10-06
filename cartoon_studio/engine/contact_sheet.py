from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw

from cartoon_studio.config import LoadedProject
from cartoon_studio.renderers.image_renderer import ImageRenderer
from cartoon_studio.utils.paths import output_root


def create_contact_sheet(project: LoadedProject) -> Path:
    renderer = ImageRenderer(320, 180, min(12, project.model.project.fps))
    renderer.prepare(project)
    assert renderer.timeline
    frames = [scene.start_frame for scene in renderer.timeline.scenes]
    columns = min(4, max(1, len(frames)))
    rows = math.ceil(len(frames) / columns)
    sheet = Image.new("RGB", (columns * 320, rows * 204), "#202020")
    draw = ImageDraw.Draw(sheet)
    for index, frame in enumerate(frames):
        x, y = index % columns * 320, index // columns * 204
        sheet.paste(renderer.render_frame(frame).resize((320, 180)), (x, y))
        draw.text((x + 6, y + 184), renderer.timeline.scene_at_frame(frame).id, fill="white")
    target = output_root(project.source) / "contact_sheet.jpg"
    target.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(target, quality=90)
    return target
