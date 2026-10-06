import pytest

from cartoon_studio.engine.camera_engine import CameraEngine
from cartoon_studio.models.camera import Camera


def test_camera_exact_endpoints():
    camera = Camera.model_validate({"movement": "slow_push", "from": {"x": .4, "y": .3, "zoom": 1}, "to": {"x": .6, "y": .7, "zoom": 1.2}})
    assert CameraEngine.state(camera, 0, "ease_in_out") == CameraEngine.state(camera, 0, "ease_in_out")
    start = CameraEngine.state(camera, 0, "ease_in_out"); end = CameraEngine.state(camera, 1, "ease_in_out")
    assert (start.x, start.y, start.zoom) == pytest.approx((.4, .3, 1))
    assert (end.x, end.y, end.zoom) == pytest.approx((.6, .7, 1.2))


def test_static_stays_static():
    camera = Camera()
    assert CameraEngine.state(camera, .1, "linear") == CameraEngine.state(camera, .9, "linear")

