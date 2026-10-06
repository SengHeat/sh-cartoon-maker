from __future__ import annotations

from typing import Literal

from pydantic import Field

from .common import Position, ScaleMode, StrictModel, UnitFloat


class Background(StrictModel):
    source: str
    scale: ScaleMode = "cover"


class Layer(StrictModel):
    id: str
    source: str
    type: Literal["image", "character", "prop", "overlay"] = "image"
    depth: UnitFloat = 0.5
    opacity: UnitFloat = 1.0
    position: Position = Field(default_factory=Position)
    scale: float = Field(default=1.0, gt=0.0)
    scale_mode: ScaleMode = "native"
    # When omitted, characters use the documented feet pivot (bottom-center),
    # while all other layer types use their geometric center.
    anchor: Position | None = None
