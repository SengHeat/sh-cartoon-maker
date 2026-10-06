from __future__ import annotations

from pydantic import Field

from .common import StrictModel, UnitFloat


class AudioClip(StrictModel):
    source: str
    start: float = Field(default=0.0, ge=0.0)
    volume: UnitFloat = 1.0
    loop: bool = False
    fade_in: float = Field(default=0.0, ge=0.0)
    fade_out: float = Field(default=0.0, ge=0.0)


class ProjectAudio(StrictModel):
    narration: str | None = None
    background_music: str | None = None

