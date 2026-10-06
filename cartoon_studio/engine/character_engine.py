from __future__ import annotations

import math
from dataclasses import dataclass

from cartoon_studio.models.character import Character
from cartoon_studio.presets.emotion import EMOTION_PRESETS
from cartoon_studio.utils.interpolation import clamp


@dataclass(frozen=True)
class CharacterState:
    x: float = 0.0
    y: float = 0.0
    rotation: float = 0.0
    scale: float = 1.0
    opacity: float = 1.0


class CharacterEngine:
    @staticmethod
    def state(character: Character, seconds: float, progress: float) -> CharacterState:
        action = character.motion.type if character.motion else character.action
        intensity = character.motion.intensity if character.motion else 0.3
        preset = EMOTION_PRESETS[character.emotion]
        speed = float(preset.get("breathing_speed", 1.0))
        phase = seconds * math.tau * speed
        x = y = rotation = 0.0
        scale = 1.0 + math.sin(phase) * float(preset.get("scale_pulse", 0.0))
        opacity = 1.0
        if action == "subtle_breathing": scale += math.sin(phase) * 0.008 * intensity
        elif action in {"walk_in_place", "walk", "run"}:
            pace = 3.5 if action == "run" else 2.0
            y = abs(math.sin(seconds * math.tau * pace)) * -0.012 * intensity
            rotation = math.sin(seconds * math.tau * pace) * 2 * intensity
        elif action == "look_left": x = -0.01 * intensity
        elif action == "look_right": x = 0.01 * intensity
        elif action == "turn_head": x = 0.008 * intensity
        elif action == "nod": y = abs(math.sin(seconds * math.tau * 1.5)) * 0.012 * intensity; rotation = math.sin(seconds * math.tau * 1.5) * 3 * intensity
        elif action == "shake": x = math.sin(seconds * math.tau * 11) * 0.012 * intensity
        elif action == "float": y = math.sin(seconds * math.tau * 0.6) * 0.025 * intensity
        elif action in {"raise_arm", "point"}: rotation = -3 * intensity
        elif action == "wave": rotation = math.sin(seconds * math.tau * 2.5) * 5 * intensity
        elif action == "fade_in": opacity = clamp(progress * 2)
        elif action == "fade_out": opacity = clamp((1 - progress) * 2)
        elif action == "sit": y = 0.035 * intensity; scale *= 0.94
        elif action == "stand": y = (1 - progress) * 0.035 * intensity; scale *= 0.94 + progress * 0.06
        elif action == "fall": rotation = min(90, progress * 120) * intensity; y = progress * 0.08 * intensity
        elif action == "take": scale *= 1 + math.sin(min(1, progress * 3) * math.pi) * 0.06 * intensity
        x += math.sin(seconds * math.tau * 9.3) * float(preset.get("shake", 0.0))
        return CharacterState(x, y, rotation, scale, opacity)
