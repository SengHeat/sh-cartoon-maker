from __future__ import annotations

import math
from dataclasses import dataclass

from cartoon_studio.models.camera import Camera
from cartoon_studio.presets.camera import MOVEMENT_DEFAULTS
from cartoon_studio.utils.interpolation import ease, lerp


@dataclass(frozen=True)
class CameraState:
    x: float
    y: float
    zoom: float


class CameraEngine:
    @staticmethod
    def state(camera: Camera, progress: float, default_easing: str, frame: int = 0, seed: int = 0) -> CameraState:
        p = ease(progress, camera.easing or default_easing)
        dx, dy, dz = MOVEMENT_DEFAULTS[camera.movement]
        start = camera.from_
        target = camera.to
        # If endpoints are untouched, semantic movement supplies a useful target.
        if target.x == start.x and target.y == start.y and target.zoom == start.zoom:
            tx, ty, tz = start.x + dx, start.y + dy, max(0.01, start.zoom + dz)
        else:
            tx, ty, tz = target.x, target.y, target.zoom
        x, y, zoom = lerp(start.x, tx, p), lerp(start.y, ty, p), lerp(start.zoom, tz, p)
        if camera.movement == "handheld_subtle" and 0 < progress < 1:
            x += math.sin((frame + seed) * 1.71) * 0.0025
            y += math.cos((frame + seed) * 1.37) * 0.0025
        return CameraState(x, y, zoom)

