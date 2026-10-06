from __future__ import annotations


class ParallaxEngine:
    @staticmethod
    def offset(camera_x: float, camera_y: float, depth: float, width: int, height: int) -> tuple[float, float]:
        # Depth 0 is fixed at infinity; depth 1 receives the full stylized shift.
        return (0.5 - camera_x) * width * depth, (0.5 - camera_y) * height * depth

