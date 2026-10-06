from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from .audio import AudioClip
from .camera import Camera
from .character import Character
from .common import StrictModel
from .effects import Effect
from .layer import Background, Layer


class Transition(StrictModel):
    type: Literal["cut", "crossfade", "fade_black"] = "cut"
    duration: float = Field(default=0.0, ge=0.0)


class Scene(StrictModel):
    id: str = Field(min_length=1)
    start: float | None = Field(default=None, ge=0.0)
    duration: float = Field(gt=0.0)
    background: Background
    layers: list[Layer] = Field(default_factory=list)
    camera: Camera = Field(default_factory=Camera)
    characters: list[Character] = Field(default_factory=list)
    effects: list[Effect] = Field(default_factory=list)
    audio: list[AudioClip] = Field(default_factory=list)
    transition_out: Transition = Field(default_factory=Transition)

    @model_validator(mode="after")
    def references_existing_layers(self) -> "Scene":
        layer_ids = [layer.id for layer in self.layers]
        if len(layer_ids) != len(set(layer_ids)):
            raise ValueError(f"Scene '{self.id}' contains duplicate layer IDs")
        missing = [c.layer_id for c in self.characters if c.layer_id not in layer_ids]
        if missing:
            raise ValueError(f"Scene '{self.id}' characters reference missing layers: {', '.join(missing)}")
        if self.transition_out.duration > self.duration:
            raise ValueError(f"Scene '{self.id}' transition exceeds its duration")
        return self

