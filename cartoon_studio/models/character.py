from __future__ import annotations

from typing import Literal

from pydantic import Field

from .common import Position, StrictModel, UnitFloat

Emotion = Literal[
    "neutral", "calm", "worried", "scared", "angry", "sad", "shocked", "ghostly",
    "happy", "serious", "tired", "glow", "menace", "looming", "sorrowful", "sneaky",
    "cheeky", "alert", "greedy",
]
Action = Literal[
    "idle", "subtle_breathing", "walk_in_place", "walk", "run", "look_left", "look_right",
    "turn_head", "nod", "shake", "raise_arm", "point", "wave", "float", "fade_in",
    "fade_out", "sit", "stand", "fall", "take",
]


class Motion(StrictModel):
    type: Action = "idle"
    intensity: UnitFloat = 0.3


class Mouth(StrictModel):
    closed: str
    open: str


class Character(StrictModel):
    layer_id: str
    emotion: Emotion = "neutral"
    action: Action = "idle"
    motion: Motion | None = None
    mouth: Mouth | None = None
    action_target: Position | None = None
    dialogue_audio: str | None = None
    auto_blink: bool = True
