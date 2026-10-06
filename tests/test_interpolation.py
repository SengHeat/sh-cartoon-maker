import pytest

from cartoon_studio.utils.interpolation import ease, lerp


@pytest.mark.parametrize("kind", ["linear", "ease_in", "ease_out", "ease_in_out"])
def test_easing_endpoints_and_bounds(kind):
    assert ease(0, kind) == pytest.approx(0)
    assert ease(1, kind) == pytest.approx(1)
    assert 0 <= ease(0.35, kind) <= 1
    assert lerp(2, 4, ease(0, kind)) == 2
    assert lerp(2, 4, ease(1, kind)) == 4

