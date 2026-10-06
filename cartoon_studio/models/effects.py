from typing import Literal

from pydantic import Field

from .common import StrictModel, UnitFloat

EffectType = Literal["vignette", "fog", "film_grain", "fade", "flash", "shake", "darken", "desaturate"]


class Effect(StrictModel):
    type: EffectType
    intensity: UnitFloat = 0.5
    speed: float = Field(default=0.1, ge=0.0)
    source: str | None = None
