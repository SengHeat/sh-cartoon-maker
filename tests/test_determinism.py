from io import BytesIO

from cartoon_studio.config import load_project
from cartoon_studio.renderers.image_renderer import ImageRenderer


def test_frame_bytes_are_repeatable(project_file):
    renderer = ImageRenderer(); renderer.prepare(load_project(project_file))
    outputs = []
    for _ in range(2):
        stream = BytesIO(); renderer.render_frame(2).save(stream, format="PNG"); outputs.append(stream.getvalue())
    assert outputs[0] == outputs[1]
    assert renderer.signature(2) == renderer.signature(2)

