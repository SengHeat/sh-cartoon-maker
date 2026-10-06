from __future__ import annotations

import math
import wave
from pathlib import Path

from PIL import Image

from cartoon_studio.models import Character, RigDefinition, load_rig


class RigEngine:
    """Small deterministic cut-out puppet compositor used by ImageRenderer."""

    def __init__(self, assets: object | None = None) -> None:
        self._rigs: dict[Path, RigDefinition] = {}
        self._images: dict[Path, Image.Image] = {}

    def _image(self, path: Path) -> Image.Image:
        if path not in self._images:
            self._images[path] = Image.open(path).convert("RGBA")
        return self._images[path].copy()

    @staticmethod
    def _mouth_state(audio: Path | None, seconds: float) -> str:
        if audio is None or not audio.is_file() or audio.suffix.lower() != ".wav":
            return "closed"
        try:
            with wave.open(str(audio), "rb") as stream:
                rate = stream.getframerate()
                channels = stream.getnchannels()
                width = stream.getsampwidth()
                start = max(0, int(seconds * rate))
                stream.setpos(min(start, stream.getnframes()))
                raw = stream.readframes(max(1, rate // 30))
            if not raw or width not in (1, 2):
                return "closed"
            if width == 1:
                level = sum(abs(value - 128) for value in raw) / len(raw) / 128
            else:
                import array
                values = array.array("h"); values.frombytes(raw)
                level = sum(abs(value) for value in values) / max(1, len(values)) / 32768
            return "wide" if level > 0.25 else "small" if level > 0.04 else "closed"
        except (wave.Error, EOFError, OSError):
            return "closed"

    def render(self, rig_path: Path, character: Character, seconds: float, progress: float,
               frame: int, fps: int, seed: int, dialogue: Path | None = None) -> Image.Image:
        rig_path = rig_path.resolve()
        rig = self._rigs.setdefault(rig_path, load_rig(rig_path))
        loaded = {name: self._image(rig_path.parent / part.image) for name, part in rig.parts.items()}
        width = max(image.width for image in loaded.values())
        height = max(image.height for image in loaded.values())
        canvas = Image.new("RGBA", (width, height))
        mouth = self._mouth_state(dialogue, seconds)
        blink = character.auto_blink and ((frame + seed * 17) % max(2, fps * 4) in (0, 1))
        for name, part in sorted(rig.parts.items(), key=lambda item: (item[1].z, item[0])):
            relative = part.image
            if name == "mouth":
                relative = part.swap.get(mouth, part.swap.get("closed", relative))
            elif name == "eyes" and blink:
                relative = part.swap.get("closed", relative)
            image = self._image(rig_path.parent / relative)
            # Source layers use a shared registered canvas, so z compositing preserves joints.
            canvas.alpha_composite(image, ((width - image.width) // 2, (height - image.height) // 2))
        return canvas
