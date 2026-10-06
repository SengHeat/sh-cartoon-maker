from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class PartPose:
    x: float = 0.0
    y: float = 0.0
    rotation: float = 0.0
    scale: float = 1.0
    opacity: float = 1.0


def action_pose(action: str, seconds: float, progress: float, intensity: float = 1.0) -> dict[str, PartPose]:
    phase = seconds * math.tau
    poses: dict[str, PartPose] = {}
    if action in {"subtle_breathing", "idle"}:
        poses["head"] = PartPose(y=math.sin(phase * 0.6) * 2 * intensity, rotation=math.sin(phase * 0.25) * 0.6 * intensity)
    elif action in {"walk", "walk_in_place", "run"}:
        speed = 3.2 if action == "run" else 1.8
        poses["body"] = PartPose(y=-abs(math.sin(phase * speed)) * 8 * intensity, rotation=math.sin(phase * speed) * 2 * intensity)
        poses["arm_l"] = PartPose(rotation=math.sin(phase * speed) * 24 * intensity)
        poses["arm_r"] = PartPose(rotation=-math.sin(phase * speed) * 24 * intensity)
    elif action in {"look_left", "look_right", "turn_head"}:
        direction = -1 if action == "look_left" else 1
        poses["head"] = PartPose(x=direction * 8 * intensity, rotation=direction * 3 * intensity)
    elif action == "nod": poses["head"] = PartPose(y=abs(math.sin(phase * 1.5)) * 8 * intensity, rotation=math.sin(phase * 1.5) * 6 * intensity)
    elif action == "shake": poses["head"] = PartPose(x=math.sin(phase * 5) * 8 * intensity, rotation=math.sin(phase * 5) * 4 * intensity)
    elif action == "raise_arm": poses["arm_r"] = PartPose(rotation=-80 * intensity)
    elif action == "point": poses["arm_r"] = PartPose(x=8 * intensity, rotation=-95 * intensity)
    elif action == "wave": poses["arm_r"] = PartPose(rotation=(-75 + math.sin(phase * 2.5) * 25) * intensity)
    elif action == "float": poses["body"] = PartPose(y=math.sin(phase * 0.5) * 12 * intensity)
    elif action == "fade_in": poses["body"] = PartPose(opacity=min(1.0, progress * 2))
    elif action == "fade_out": poses["body"] = PartPose(opacity=min(1.0, (1 - progress) * 2))
    elif action == "sit": poses["body"] = PartPose(y=35 * intensity, scale=0.94)
    elif action == "stand": poses["body"] = PartPose(y=(1 - progress) * 35 * intensity, scale=0.94 + progress * 0.06)
    elif action == "fall": poses["body"] = PartPose(rotation=min(90, progress * 120) * intensity, y=progress * 80 * intensity)
    elif action == "take": poses["body"] = PartPose(y=-math.sin(min(1, progress * 3) * math.pi) * 25 * intensity, scale=1 + math.sin(min(1, progress * 3) * math.pi) * 0.06)
    return poses

