from __future__ import annotations

import json
from pathlib import Path

from PIL import Image


class SpriteAnimationEngine:
    """Loads optional ``anim/<action>`` frame sequences beside a base sprite."""

    def __init__(self) -> None:
        self._cache: dict[tuple[Path, str], tuple[Image.Image, ...]] = {}

    @staticmethod
    def _directory(source: Path, action: str) -> Path:
        return source.parent / "anim" / action

    def has_animation(self, source: Path, action: str) -> bool:
        folder = self._directory(source, action)
        if folder.is_dir() and any(folder.glob("*.png")):
            return True
        return (source.parent / f"{action}.frames.json").is_file()

    def _frames(self, source: Path, action: str) -> tuple[Image.Image, ...]:
        key = (source.resolve(), action)
        if key in self._cache:
            return self._cache[key]
        folder = self._directory(source, action)
        paths = sorted(folder.glob("*.png")) if folder.is_dir() else []
        frames: list[Image.Image] = [Image.open(path).convert("RGBA") for path in paths]
        index_path = source.parent / f"{action}.frames.json"
        if not frames and index_path.is_file():
            data = json.loads(index_path.read_text(encoding="utf-8"))
            sheet = Image.open(source.parent / data["image"]).convert("RGBA")
            for box in data["frames"]:
                frames.append(sheet.crop(tuple(box)))
        self._cache[key] = tuple(frames)
        return self._cache[key]

    def frame(self, source: Path, action: str, seconds: float) -> Image.Image | None:
        frames = self._frames(source, action)
        if not frames:
            return None
        # Asset sequences intentionally use a stable 12 fps default.
        return frames[int(max(0.0, seconds) * 12) % len(frames)].copy()
