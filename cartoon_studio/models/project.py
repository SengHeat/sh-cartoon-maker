from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from .audio import ProjectAudio
from .common import Easing, StrictModel, UnitFloat
from .scene import Scene


class Resolution(StrictModel):
    width: int = Field(gt=0)
    height: int = Field(gt=0)


class ProjectSettings(StrictModel):
    title: str
    mode: Literal["2d", "2.5d", "3d"] = "2.5d"
    resolution: Resolution
    fps: int = Field(gt=0, le=240)
    background_color: str = Field(default="#000000", pattern=r"^#[0-9a-fA-F]{6}$")
    seed: int = 42
    timing_mode: Literal["narration_driven", "scenes_driven"] = "narration_driven"


class Defaults(StrictModel):
    transition_duration: float = Field(default=1.0, ge=0.0)
    camera_easing: Easing = "ease_in_out"
    music_volume: UnitFloat = 0.15
    narration_volume: UnitFloat = 1.0
    sfx_volume: UnitFloat = 0.55


class Project(StrictModel):
    format_version: Literal[1] = 1
    project: ProjectSettings
    defaults: Defaults = Field(default_factory=Defaults)
    audio: ProjectAudio = Field(default_factory=ProjectAudio)
    scenes: list[Scene] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_scene_ids(self) -> "Project":
        ids = [scene.id for scene in self.scenes]
        if len(ids) != len(set(ids)):
            duplicates = sorted({item for item in ids if ids.count(item) > 1})
            raise ValueError(f"Duplicate scene ID(s): {', '.join(duplicates)}")
        return self

