import pytest

from cartoon_studio.engine.parallax_engine import ParallaxEngine


def test_foreground_moves_more():
    far = ParallaxEngine.offset(.6, .4, .1, 100, 100)
    near = ParallaxEngine.offset(.6, .4, .9, 100, 100)
    assert abs(near[0]) > abs(far[0])
    assert ParallaxEngine.offset(.6, .4, 0, 100, 100) == (0, 0)
    assert ParallaxEngine.offset(.6, .4, 1, 100, 100) == pytest.approx((-10, 10))
