from __future__ import annotations

import json
import difflib
import wave
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from .models import Project, load_rig


class ProjectError(RuntimeError):
    """Base error for project loading and preflight validation."""


class AssetNotFoundError(ProjectError):
    pass


class TimingError(ProjectError):
    pass


@dataclass(frozen=True)
class LoadedProject:
    model: Project
    source: Path
    root: Path
    duration: float
    scene_durations: tuple[float, ...]

    def resolve(self, value: str) -> Path:
        path = Path(value)
        return path if path.is_absolute() else (self.root / path).resolve()


def _audio_duration(path: Path) -> float:
    try:
        with wave.open(str(path), "rb") as stream:
            return stream.getnframes() / stream.getframerate()
    except (wave.Error, EOFError) as exc:
        raise TimingError(f"Cannot read narration duration from '{path}': {exc}") from exc


def collect_assets(project: Project) -> list[tuple[str, str]]:
    assets: list[tuple[str, str]] = []
    if project.audio.narration:
        assets.append(("project narration", project.audio.narration))
    if project.audio.background_music:
        assets.append(("project background music", project.audio.background_music))
    for scene in project.scenes:
        assets.append((f"Scene '{scene.id}' background", scene.background.source))
        assets.extend((f"Scene '{scene.id}' layer '{layer.id}'", layer.source) for layer in scene.layers)
        for character in scene.characters:
            if character.dialogue_audio:
                assets.append((f"Scene '{scene.id}' character '{character.layer_id}' dialogue", character.dialogue_audio))
            if character.mouth:
                # Mouth assets are deliberately optional in V1.
                continue
        assets.extend((f"Scene '{scene.id}' effect", e.source) for e in scene.effects if e.source)
        assets.extend((f"Scene '{scene.id}' audio", clip.source) for clip in scene.audio)
    return assets


def _project_root(source: Path) -> Path:
    """Find the containing Cartoon Studio workspace for portable story folders."""
    for candidate in (source.parent, *source.parents):
        if (candidate / "pyproject.toml").is_file() and (candidate / "assets").is_dir():
            return candidate
    # Standalone projects conventionally keep assets next to the JSON. Retain
    # compatibility with the original projects/<story>.json layout as fallback.
    return source.parent.parent if source.parent.name == "projects" else source.parent


def load_project(path: str | Path, *, validate_assets: bool = True) -> LoadedProject:
    source = Path(path).expanduser().resolve()
    if not source.is_file():
        raise ProjectError(f"Project file not found: {source}")
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
        model = Project.model_validate(data)
    except json.JSONDecodeError as exc:
        raise ProjectError(f"Invalid JSON in {source}: line {exc.lineno}, column {exc.colno}: {exc.msg}") from exc
    except ValidationError as exc:
        raise ProjectError(f"Project validation failed:\n{exc}") from exc
    if model.project.mode == "3d":
        raise ProjectError("3D rendering is not implemented yet. Use mode=2.5d or install/enable BlenderRenderer.")

    # Asset paths are relative to the process/project workspace, matching JSON examples.
    root = _project_root(source)
    if validate_assets:
        for context, value in collect_assets(model):
            resolved = Path(value) if Path(value).is_absolute() else root / value
            if not resolved.is_file():
                candidates = [str(item.relative_to(root)) for item in (root / "assets").rglob("*") if item.is_file()] if (root / "assets").exists() else []
                matches = difflib.get_close_matches(value, candidates, n=3, cutoff=0.45)
                suggestion = f"\nDid you mean: {', '.join(matches)}" if matches else ""
                raise AssetNotFoundError(f"{context} references missing asset:\n{value}{suggestion}")
        for scene in model.scenes:
            characters = {item.layer_id for item in scene.characters}
            for layer in scene.layers:
                if layer.id not in characters:
                    continue
                source_path = Path(layer.source) if Path(layer.source).is_absolute() else root / layer.source
                rig_path = source_path.parent / "rig.json"
                if rig_path.is_file():
                    try:
                        load_rig(rig_path)
                    except (ValueError, OSError) as exc:
                        raise ProjectError(f"Invalid puppet rig for scene '{scene.id}', character '{layer.id}': {exc}") from exc

    hints = tuple(scene.duration for scene in model.scenes)
    scene_total = sum(hints)
    narration_duration: float | None = None
    if model.audio.narration:
        narration = Path(model.audio.narration) if Path(model.audio.narration).is_absolute() else root / model.audio.narration
        if narration.is_file():
            narration_duration = _audio_duration(narration)

    if model.project.timing_mode == "narration_driven" and narration_duration is not None:
        if scene_total <= 0:
            raise TimingError("Scene duration sum must be positive")
        factor = narration_duration / scene_total
        durations = tuple(value * factor for value in hints)
        duration = narration_duration
    else:
        durations = hints
        duration = scene_total
        if model.project.timing_mode == "scenes_driven" and narration_duration and narration_duration > duration + 1 / model.project.fps:
            delta = narration_duration - duration
            raise TimingError(
                f"Narration is longer than the scene timeline: narration={narration_duration:.3f}s, "
                f"scenes={duration:.3f}s, delta={delta:.3f}s. Audio is never silently truncated."
            )
    return LoadedProject(model, source, root.resolve(), duration, durations)
