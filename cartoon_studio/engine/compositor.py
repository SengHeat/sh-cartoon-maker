from __future__ import annotations

from collections import OrderedDict
from pathlib import Path

from PIL import Image


class AssetManager:
    """Bounded, process-local decoded image cache."""

    def __init__(self, max_items: int = 32):
        self.max_items = max_items
        self._images: OrderedDict[Path, Image.Image] = OrderedDict()

    def get_image(self, path: Path) -> Image.Image:
        path = path.resolve()
        if path in self._images:
            self._images.move_to_end(path)
            return self._images[path]
        with Image.open(path) as source:
            image = source.convert("RGBA").copy()
        self._images[path] = image
        if len(self._images) > self.max_items:
            self._images.popitem(last=False)
        return image


def scaled(image: Image.Image, mode: str, canvas: tuple[int, int], scale: float = 1.0) -> Image.Image:
    width, height = canvas
    if mode == "stretch":
        size = (width, height)
    elif mode in {"contain", "cover"}:
        ratio = min(width / image.width, height / image.height) if mode == "contain" else max(width / image.width, height / image.height)
        size = (max(1, round(image.width * ratio)), max(1, round(image.height * ratio)))
    else:
        size = (max(1, round(image.width * scale)), max(1, round(image.height * scale)))
    if mode != "native":
        size = (max(1, round(size[0] * scale)), max(1, round(size[1] * scale)))
    return image.resize(size, Image.Resampling.LANCZOS) if size != image.size else image.copy()


def paste_centered(canvas: Image.Image, image: Image.Image, x: float, y: float, anchor: tuple[float, float] = (0.5, 0.5)) -> None:
    left = round(x - image.width * anchor[0])
    top = round(y - image.height * anchor[1])
    canvas.alpha_composite(image, (left, top))

