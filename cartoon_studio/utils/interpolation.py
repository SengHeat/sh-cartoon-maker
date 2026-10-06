from __future__ import annotations

import math


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def ease(progress: float, kind: str = "linear") -> float:
    t = clamp(progress)
    if kind == "linear":
        return t
    if kind == "ease_in":
        return t * t
    if kind == "ease_out":
        return 1 - (1 - t) ** 2
    if kind == "ease_in_out":
        return 0.5 - math.cos(math.pi * t) / 2
    raise ValueError(f"Unsupported easing: {kind}")


def lerp(start: float, end: float, progress: float) -> float:
    return start + (end - start) * progress

