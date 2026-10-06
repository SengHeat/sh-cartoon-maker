from typing import Literal

from pydantic import Field

from .common import CameraPoint, Easing, StrictModel

CameraMovement = Literal[
    "static", "slow_push", "slow_pull", "pan_left", "pan_right",
    "pan_up", "pan_down", "drift_left", "drift_right", "handheld_subtle",
]


class Camera(StrictModel):
    shot: Literal["wide", "medium", "close", "extreme_close"] = "wide"
    movement: CameraMovement = "static"
    from_: CameraPoint = Field(default_factory=CameraPoint, alias="from")
    to: CameraPoint = Field(default_factory=CameraPoint)
    easing: Easing | None = None

