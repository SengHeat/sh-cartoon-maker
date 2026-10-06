from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class EnvironmentError(ValueError):
    """Raised when an environment asset is missing or inconsistent."""


def _point(value: Any, label: str) -> tuple[float, float, float]:
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise EnvironmentError(f"{label} must contain three numbers")
    return tuple(float(item) for item in value)


@dataclass(frozen=True)
class Zone:
    """Axis-aligned semantic environment zone."""

    name: str
    minimum: tuple[float, float]
    maximum: tuple[float, float]

    def contains(self, x: float, y: float, margin: float = 0.0) -> bool:
        return self.minimum[0]-margin <= x <= self.maximum[0]+margin and self.minimum[1]-margin <= y <= self.maximum[1]+margin


@dataclass(frozen=True)
class CameraMark:
    location: tuple[float, float, float]
    target: tuple[float, float, float]
    lens: float = 50.0


@dataclass(frozen=True)
class EnvironmentDefinition:
    id: str
    type: str
    seed: int
    ground: dict[str, Any]
    lighting: dict[str, Any]
    zones: dict[str, Zone]
    spawn_points: dict[str, tuple[float, float, float]]
    prop_points: dict[str, tuple[float, float, float]]
    camera_marks: dict[str, CameraMark]
    vegetation: dict[str, Any] = field(default_factory=dict)
    wind: dict[str, Any] = field(default_factory=dict)
    foreground: bool = True

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EnvironmentDefinition":
        for key in ("id", "type", "ground", "lighting", "zones", "spawn_points", "prop_points", "camera_marks"):
            if key not in data:
                raise EnvironmentError(f"Environment definition is missing required field: {key}")
        zones: dict[str, Zone] = {}
        for name, value in data["zones"].items():
            if not isinstance(value, dict) or "min" not in value or "max" not in value:
                raise EnvironmentError(f"Zone '{name}' requires min and max")
            minimum, maximum = value["min"], value["max"]
            if len(minimum) != 2 or len(maximum) != 2:
                raise EnvironmentError(f"Zone '{name}' bounds must be 2D")
            zones[str(name)] = Zone(str(name), tuple(map(float, minimum)), tuple(map(float, maximum)))
        marks = {
            str(name): CameraMark(_point(value["location"], f"Camera mark '{name}' location"), _point(value["target"], f"Camera mark '{name}' target"), float(value.get("lens", 50)))
            for name, value in data["camera_marks"].items()
        }
        result = cls(
            str(data["id"]), str(data["type"]), int(data.get("seed", 42)), dict(data["ground"]), dict(data["lighting"]), zones,
            {str(k): _point(v, f"Spawn point '{k}'") for k, v in data["spawn_points"].items()},
            {str(k): _point(v, f"Prop point '{k}'") for k, v in data["prop_points"].items()}, marks,
            dict(data.get("vegetation", {})), dict(data.get("wind", {})), bool(data.get("foreground", True)),
        )
        required_zones = {"action", "background", "foreground", "left_forest", "right_forest", "path", "prop"}
        missing = sorted(required_zones-result.zones.keys())
        if missing:
            raise EnvironmentError(f"{result.id} is missing zones: {', '.join(missing)}")
        if not result.ground.get("walkable", False):
            raise EnvironmentError(f"{result.id} ground must define a walkable area")
        return result

    def spawn_point(self, name: str) -> tuple[float, float, float]:
        try: return self.spawn_points[name]
        except KeyError as exc: raise EnvironmentError(f"Unknown spawn point '{name}' in {self.id}") from exc

    def prop_point(self, name: str) -> tuple[float, float, float]:
        try: return self.prop_points[name]
        except KeyError as exc: raise EnvironmentError(f"Unknown prop point '{name}' in {self.id}") from exc

    def zone(self, name: str) -> Zone:
        try: return self.zones[name]
        except KeyError as exc: raise EnvironmentError(f"Unknown zone '{name}' in {self.id}") from exc

    def camera_mark(self, name: str) -> CameraMark:
        try: return self.camera_marks[name]
        except KeyError as exc: raise EnvironmentError(f"Unknown camera mark '{name}' in {self.id}") from exc

    def is_walkable(self, position: tuple[float, float, float] | tuple[float, float]) -> bool:
        return self.zone("action").contains(float(position[0]), float(position[1])) or self.zone("path").contains(float(position[0]), float(position[1]))

    def ground_height(self, x: float, y: float) -> float:
        """Small deterministic undulation, kept flat through the core action strip."""
        if self.zone("action").contains(x, y):
            return float(self.ground.get("base_height", 0.0))
        amplitude = min(.12, abs(float(self.ground.get("variation", .08))))
        return float(self.ground.get("base_height", 0.0)) + amplitude * math.sin(x*.31) * math.cos(y*.27)

    def ground_normal(self, x: float, y: float) -> tuple[float, float, float]:
        epsilon=.02
        dx=(self.ground_height(x+epsilon,y)-self.ground_height(x-epsilon,y))/(epsilon*2)
        dy=(self.ground_height(x,y+epsilon)-self.ground_height(x,y-epsilon))/(epsilon*2)
        length=math.sqrt(dx*dx+dy*dy+1)
        return (-dx/length,-dy/length,1/length)


def load_environment_definition(path: str | Path) -> EnvironmentDefinition:
    source=Path(path)
    try: return EnvironmentDefinition.from_dict(json.loads(source.read_text(encoding="utf-8")))
    except json.JSONDecodeError as exc: raise EnvironmentError(f"Invalid environment JSON {source}: {exc}") from exc
