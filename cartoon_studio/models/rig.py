from __future__ import annotations

import json
from pathlib import Path

from pydantic import Field, model_validator

from .common import StrictModel, UnitFloat


class RigPoint(StrictModel):
    """Normalized coordinate within a puppet part image."""

    x: UnitFloat = 0.5
    y: UnitFloat = 0.5


class RigPart(StrictModel):
    image: str
    parent: str | None = None
    attach: tuple[UnitFloat, UnitFloat] = (0.5, 0.5)
    pivot: tuple[UnitFloat, UnitFloat] = (0.5, 0.5)
    z: int = 0
    swap: dict[str, str] = Field(default_factory=dict)


class RigDefinition(StrictModel):
    rig_version: int = Field(default=1, ge=1)
    parts: dict[str, RigPart]

    @model_validator(mode="after")
    def validate_graph(self) -> "RigDefinition":
        if not self.parts:
            raise ValueError("rig must contain at least one part")
        for name, part in self.parts.items():
            if part.parent == name:
                raise ValueError(f"rig part '{name}' cannot parent itself")
            if part.parent and part.parent not in self.parts:
                raise ValueError(f"rig part '{name}' references missing parent '{part.parent}'")
        for name in self.parts:
            seen: set[str] = set()
            cursor: str | None = name
            while cursor:
                if cursor in seen:
                    raise ValueError(f"rig contains a parent cycle at '{cursor}'")
                seen.add(cursor)
                cursor = self.parts[cursor].parent
        return self


def load_rig(path: str | Path) -> RigDefinition:
    source = Path(path)
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
        rig = RigDefinition.model_validate(data)
    except (json.JSONDecodeError, OSError) as exc:
        raise ValueError(f"cannot load rig '{source}': {exc}") from exc
    for name, part in rig.parts.items():
        for relative in (part.image, *part.swap.values()):
            asset = source.parent / relative
            if not asset.is_file():
                raise ValueError(f"rig part '{name}' references missing image '{relative}'")
    return rig
