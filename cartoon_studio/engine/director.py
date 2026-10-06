from __future__ import annotations

import json
import importlib
import logging
import os
import shutil
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image

from cartoon_studio.config import LoadedProject, collect_assets, load_project
from cartoon_studio.engine.timeline import Timeline
from cartoon_studio.renderers.base import BaseRenderer
from cartoon_studio.renderers.image_renderer import ImageRenderer
from cartoon_studio.utils.hashing import file_fingerprint, stable_hash
from cartoon_studio.utils.paths import frame_path, output_root

LOGGER = logging.getLogger(__name__)
_WORKER_RENDERER: BaseRenderer | None = None
_WORKER_FRAMES: Path | None = None


def _valid_png(path: Path, expected: tuple[int, int]) -> bool:
    if not path.is_file():
        return False
    try:
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            return image.size == expected
    except (OSError, SyntaxError):
        return False


def _worker_init(project_path: str, width: int | None, height: int | None, fps: int | None, frames: str, renderer_name: str) -> None:
    global _WORKER_RENDERER, _WORKER_FRAMES
    project = load_project(project_path)
    module_name, class_name = renderer_name.split(":", 1)
    renderer_type = getattr(importlib.import_module(module_name), class_name)
    _WORKER_RENDERER = renderer_type(width, height, fps)
    _WORKER_RENDERER.prepare(project)
    _WORKER_FRAMES = Path(frames)


def _worker_render(frame: int) -> int:
    assert _WORKER_RENDERER is not None and _WORKER_FRAMES is not None
    destination = frame_path(_WORKER_FRAMES, frame)
    temporary = destination.with_suffix(".tmp.png")
    _WORKER_RENDERER.render_frame(frame).save(temporary, format="PNG", optimize=False)
    temporary.replace(destination)
    return frame


@dataclass(frozen=True)
class RenderResult:
    output_dir: Path
    frames_dir: Path
    total_frames: int
    rendered: int
    reused: int


class Director:
    def __init__(self, renderer_factory: type[BaseRenderer] = ImageRenderer):
        self.renderer_factory = renderer_factory

    @staticmethod
    def _scene_hashes(project: LoadedProject) -> dict[str, str]:
        result: dict[str, str] = {}
        for scene in project.model.scenes:
            values = [scene.model_dump(mode="json", by_alias=True), project.model.defaults.model_dump(mode="json")]
            paths = [scene.background.source, *(layer.source for layer in scene.layers), *(clip.source for clip in scene.audio), *(e.source for e in scene.effects if e.source)]
            paths.extend(character.dialogue_audio for character in scene.characters if character.dialogue_audio)
            for value in paths:
                path = project.resolve(value)
                values.append(file_fingerprint(path))
            character_ids = {character.layer_id for character in scene.characters}
            for layer in scene.layers:
                if layer.id not in character_ids:
                    continue
                character_root = project.resolve(layer.source).parent
                for asset in sorted(character_root.rglob("*")):
                    if asset.is_file() and (asset.name == "rig.json" or "parts" in asset.parts or "anim" in asset.parts):
                        values.append(file_fingerprint(asset))
            result[scene.id] = stable_hash(values)
        return result

    @staticmethod
    def _manifest(project: LoadedProject, timeline: Timeline, width: int, height: int, scene_hashes: dict[str, str]) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        return {
            "format_version": 1,
            "project_hash": stable_hash(project.model.model_dump(mode="json", by_alias=True)),
            "scene_hashes": scene_hashes,
            "seed": project.model.project.seed,
            "fps": timeline.fps,
            "resolution": [width, height],
            "total_frames": timeline.total_frames,
            "completed_frames": 0,
            "started_at": now,
            "updated_at": now,
            "status": "rendering",
        }

    def render(
        self, project: LoadedProject, *, workers: int | None = None, resume: bool = False,
        force: bool = False, preview: bool = False, from_seconds: float | None = None,
        to_seconds: float | None = None, scene_id: str | None = None, dedupe: bool = True,
    ) -> RenderResult:
        settings = project.model.project
        width, height = (min(960, settings.resolution.width), min(540, settings.resolution.height)) if preview else (settings.resolution.width, settings.resolution.height)
        fps = min(12, settings.fps) if preview else settings.fps
        renderer_factory = self.renderer_factory
        if renderer_factory is ImageRenderer and any(scene.renderer == "blender" for scene in project.model.scenes):
            from cartoon_studio.renderers.hybrid_renderer import HybridRenderer
            renderer_factory = HybridRenderer
        renderer = renderer_factory(width, height, fps)
        renderer.prepare(project)
        timeline = getattr(renderer, "timeline", None)
        if timeline is None:
            raise TypeError("Renderer.prepare() must expose its resolved timeline")
        destination = output_root(project.source)
        frames_dir = destination / "frames"
        frames_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = destination / "render_manifest.json"
        scene_hashes = self._scene_hashes(project)
        manifest = self._manifest(project, timeline, width, height, scene_hashes)
        previous: dict[str, Any] | None = None
        if manifest_path.is_file():
            try: previous = json.loads(manifest_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError: previous = None
        if resume and previous:
            global_keys = ("format_version", "seed", "fps", "resolution", "total_frames")
            changed = [key for key in global_keys if previous.get(key) != manifest.get(key)]
            if changed and not force:
                raise RuntimeError(f"Resume is unsafe because global render settings changed ({', '.join(changed)}); rerun with --force")
            manifest["started_at"] = previous.get("started_at", manifest["started_at"])

        selected = set(range(timeline.total_frames))
        if scene_id:
            matches = [item for item in timeline.scenes if item.id == scene_id]
            if not matches: raise ValueError(f"Unknown scene ID: {scene_id}")
            item = matches[0]; selected = set(range(item.start_frame, item.end_frame))
        if from_seconds is not None:
            selected = {frame for frame in selected if frame >= max(0, timeline.seconds_to_frame(from_seconds))}
        if to_seconds is not None:
            selected = {frame for frame in selected if frame < min(timeline.total_frames, timeline.seconds_to_frame(to_seconds))}

        invalid_scenes: set[str] = set()
        if resume and previous:
            invalid_scenes = {key for key, value in scene_hashes.items() if previous.get("scene_hashes", {}).get(key) != value}
        expected = (width, height)
        if force:
            tasks = sorted(selected)
        else:
            tasks = []
            for frame in sorted(selected):
                scene_changed = timeline.scene_at_frame(frame).id in invalid_scenes
                if scene_changed or not _valid_png(frame_path(frames_dir, frame), expected): tasks.append(frame)

        # Identify static equivalents before dispatch. Representatives render in parallel;
        # duplicates are hardlinked/copied afterward, avoiding races between workers.
        aliases: dict[int, int] = {}
        representatives: list[int] = []
        previous_signature: str | None = None
        previous_frame: int | None = None
        task_set = set(tasks)
        for frame in sorted(selected):
            signature = renderer.signature(frame) if dedupe else None
            if frame in task_set:
                if dedupe and signature == previous_signature and previous_frame is not None:
                    aliases[frame] = previous_frame
                else:
                    representatives.append(frame)
            previous_signature, previous_frame = signature, frame

        workers = workers or int(os.getenv("CARTOON_STUDIO_WORKERS", str(os.cpu_count() or 1)))
        # Blender shots are batch-prepared once in this process. Spawning renderer
        # workers would repeat the same headless Blender subprocess per worker.
        if renderer_factory.__name__ == "HybridRenderer":
            workers = 1
        workers = max(1, workers)
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        LOGGER.info("Project: %s | Frames: %d | Workers: %d", settings.title, len(selected), workers)
        completed = 0
        if workers == 1:
            for frame in representatives:
                destination_frame = frame_path(frames_dir, frame)
                temp = destination_frame.with_suffix(".tmp.png")
                renderer.render_frame(frame).save(temp, format="PNG", optimize=False); temp.replace(destination_frame)
                completed += 1
                self._progress(completed, len(representatives), frame)
        elif representatives:
            renderer_name = f"{renderer_factory.__module__}:{renderer_factory.__qualname__}"
            with ProcessPoolExecutor(max_workers=workers, initializer=_worker_init, initargs=(str(project.source), width, height, fps, str(frames_dir), renderer_name)) as pool:
                futures = {pool.submit(_worker_render, frame): frame for frame in representatives}
                for future in as_completed(futures):
                    frame = future.result(); completed += 1
                    self._progress(completed, len(representatives), frame)

        reused = 0
        for frame, source_frame in aliases.items():
            source = frame_path(frames_dir, source_frame)
            target = frame_path(frames_dir, frame)
            if not source.exists():  # source may itself be an alias; walk backward.
                ancestor = source_frame
                while ancestor in aliases: ancestor = aliases[ancestor]
                source = frame_path(frames_dir, ancestor)
            if target.exists(): target.unlink()
            try: os.link(source, target)
            except OSError: shutil.copy2(source, target)
            reused += 1

        complete_count = sum(_valid_png(frame_path(frames_dir, frame), expected) for frame in range(timeline.total_frames))
        manifest.update(completed_frames=complete_count, updated_at=datetime.now(timezone.utc).isoformat(), status="complete" if complete_count == timeline.total_frames else "partial")
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        renderer.finalize()
        return RenderResult(destination, frames_dir, len(selected), completed, reused)

    @staticmethod
    def _progress(done: int, total: int, frame: int) -> None:
        if done == total or done == 1 or done % max(1, total // 20) == 0:
            LOGGER.info("Frame %d / %d (%.1f%%) - frame_%06d.png", done, total, done / max(1, total) * 100, frame + 1)
