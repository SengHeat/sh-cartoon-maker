from __future__ import annotations

from enum import Enum


class LocomotionPhase(str, Enum):
    CONTACT="CONTACT"; DOWN="DOWN"; PASSING="PASSING"; UP="UP"; AIRBORNE="AIRBORNE"


def get_walk_phase(progress: float) -> LocomotionPhase:
    phase=progress%1.0
    if phase < .12:return LocomotionPhase.CONTACT
    if phase < .32:return LocomotionPhase.DOWN
    if phase < .62:return LocomotionPhase.PASSING
    if phase < .88:return LocomotionPhase.UP
    return LocomotionPhase.CONTACT


def get_run_phase(progress: float) -> LocomotionPhase:
    phase=progress%1.0
    if phase < .10:return LocomotionPhase.CONTACT
    if phase < .28:return LocomotionPhase.DOWN
    if phase < .50:return LocomotionPhase.UP
    if phase < .78:return LocomotionPhase.AIRBORNE
    return LocomotionPhase.PASSING


def is_foot_planted(progress: float, *, run: bool=False) -> bool:
    phase=progress%1.0
    return phase < (.32 if run else .62)
