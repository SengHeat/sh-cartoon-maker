from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

UnitFloat = Annotated[float, Field(ge=0.0, le=1.0)]
PositiveFloat = Annotated[float, Field(gt=0.0)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Position(StrictModel):
    """Normalized canvas coordinate: x left-to-right, y top-to-bottom."""

    x: UnitFloat = 0.5
    y: UnitFloat = 0.5


class CameraPoint(Position):
    zoom: Annotated[float, Field(gt=0.0)] = 1.0


ScaleMode = Literal["contain", "cover", "stretch", "native"]
Easing = Literal["linear", "ease_in", "ease_out", "ease_in_out"]

