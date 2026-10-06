from __future__ import annotations

import math
from dataclasses import dataclass

from cartoon_studio.config import LoadedProject


@dataclass(frozen=True)
class TimelineScene:
    id: str
    index: int
    duration: float
    start_frame: int
    end_frame: int


class Timeline:
    """Resolved, gap-free frame allocation for a loaded project."""

    def __init__(self, project: LoadedProject, fps: int | None = None) -> None:
        self.fps = fps or project.model.project.fps
        self.scenes: tuple[TimelineScene, ...] = self._build(project)
        self.total_frames = self.scenes[-1].end_frame if self.scenes else 0

    def _build(self, project: LoadedProject) -> tuple[TimelineScene, ...]:
        result: list[TimelineScene] = []
        start = 0
        elapsed = 0.0
        for index, (scene, duration) in enumerate(zip(project.model.scenes, project.scene_durations, strict=True)):
            elapsed += duration
            end = max(start + 1, round(elapsed * self.fps))
            result.append(TimelineScene(scene.id, index, duration, start, end))
            start = end
        return tuple(result)

    def scene_at_frame(self, frame: int) -> TimelineScene:
        if not 0 <= frame < self.total_frames:
            raise IndexError(f"frame {frame} outside timeline [0, {self.total_frames})")
        return next(scene for scene in self.scenes if frame < scene.end_frame)

    def local_scene_time(self, frame: int) -> float:
        scene = self.scene_at_frame(frame)
        return (frame - scene.start_frame) / self.fps

    def local_progress(self, frame: int) -> float:
        scene = self.scene_at_frame(frame)
        count = scene.end_frame - scene.start_frame
        return 0.0 if count <= 1 else (frame - scene.start_frame) / (count - 1)

    def seconds_to_frame(self, seconds: float) -> int:
        return int(math.floor(max(0.0, seconds) * self.fps + 1e-9))
