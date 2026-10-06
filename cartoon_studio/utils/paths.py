from __future__ import annotations

import os
import re
from pathlib import Path


def project_slug(path: Path) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", path.stem).strip("_") or "project"


def output_root(path: Path) -> Path:
    configured = Path(os.getenv("CARTOON_STUDIO_OUTPUT", "output"))
    return configured / project_slug(path)


def frame_path(directory: Path, index: int) -> Path:
    return directory / f"frame_{index + 1:06d}.png"

