"""Label and tile existing Blender renders without altering their aspect ratio."""
from __future__ import annotations

import argparse
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps


def make_sheet(paths: list[Path], output: Path, columns: int = 3) -> None:
    if not paths or columns < 1:
        raise ValueError("At least one image and one column are required")
    width, height, label = 427, 240, 24
    result = Image.new("RGB", (width * columns, (height + label) * math.ceil(len(paths) / columns)), "#171c23")
    draw = ImageDraw.Draw(result)
    for i, path in enumerate(paths):
        with Image.open(path) as image:
            tile = ImageOps.contain(image.convert("RGB"), (width, height))
        x, y = i % columns * width, i // columns * (height + label)
        result.paste(tile, (x + (width - tile.width) // 2, y + label + (height - tile.height) // 2))
        draw.text((x + 8, y + 5), path.stem.replace("_", " "), fill="white")
    output.parent.mkdir(parents=True, exist_ok=True)
    result.save(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--columns", type=int, default=3)
    parser.add_argument("images", nargs="+", type=Path)
    args = parser.parse_args()
    make_sheet(args.images, args.output, args.columns)
