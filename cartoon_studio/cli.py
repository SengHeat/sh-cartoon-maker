from __future__ import annotations

import argparse
import json
import logging
import shutil
import sys
from pathlib import Path

from .config import ProjectError, collect_assets, load_project
from .demo import create_demo
from .engine.director import Director
from .engine.ffmpeg_engine import FFmpegEngine
from .engine.contact_sheet import create_contact_sheet
from .engine.timeline import Timeline
from .models import Project
from .utils.logging import configure_logging
from .utils.paths import output_root
from .utils.subprocess import CommandError


def _time(seconds: float) -> str:
    total = round(seconds)
    return f"{total // 3600:02d}:{total % 3600 // 60:02d}:{total % 60:02d}"


def _details(path: str) -> tuple[object, Timeline]:
    project = load_project(path)
    return project, Timeline(project)


def _add_render_options(parser: argparse.ArgumentParser, *, scene: bool = False) -> None:
    parser.add_argument("project")
    if scene: parser.add_argument("scene_id")
    parser.add_argument("--preview", action="store_true")
    parser.add_argument("--workers", type=int)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--no-dedupe", action="store_true")
    if not scene:
        parser.add_argument("--from", dest="from_seconds", type=float)
        parser.add_argument("--to", dest="to_seconds", type=float)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cartoon-studio", description="JSON-driven deterministic cartoon video renderer")
    parser.add_argument("--verbose", action="store_true")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("validate", "info", "encode", "clean", "contact-sheet"):
        child = commands.add_parser(name); child.add_argument("project")
        if name == "encode": child.add_argument("--preview", action="store_true")
    commands.add_parser("schema")
    demo = commands.add_parser("create-demo"); demo.add_argument("--root", default="."); demo.add_argument("--full", action="store_true")
    _add_render_options(commands.add_parser("render"))
    _add_render_options(commands.add_parser("render-scene"), scene=True)
    blender = commands.add_parser("render-blender", help="render a semantic 3D story with Blender")
    blender.add_argument("project"); blender.add_argument("--preview", action="store_true"); blender.add_argument("--blend-only", action="store_true")
    blender.add_argument("--fur-quality", choices=("off","preview","medium","final"))
    blender.add_argument("--resume", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    configure_logging(args.verbose)
    try:
        if args.command == "render-blender":
            from .blender.launcher import render_story
            output = render_story(args.project, preview=args.preview, blend_only=args.blend_only,
                                  fur_quality=args.fur_quality, resume=args.resume)
            print(f"Blender output created: {output}"); return 0
        if args.command == "schema":
            print(json.dumps(Project.model_json_schema(), ensure_ascii=False, indent=2)); return 0
        if args.command == "create-demo":
            target = create_demo(Path(args.root), full=args.full)
            print(f"Demo created: {target}")
            if args.full: print(f"Full placeholder asset library created: {Path(args.root).resolve() / 'assets/manifest.json'}")
            return 0
        project = load_project(args.project)
        timeline = Timeline(project)
        if args.command in {"validate", "info"}:
            assets = {value for _, value in collect_assets(project.model)}
            if args.command == "validate": print("Project valid")
            print(f"Title: {project.model.project.title}")
            print(f"Scenes: {len(project.model.scenes)}")
            print(f"Assets: {len(assets)}")
            print(f"Timing mode: {project.model.project.timing_mode}")
            print(f"Duration: {_time(project.duration)} ({project.duration:.3f}s)")
            print(f"Resolution: {project.model.project.resolution.width}x{project.model.project.resolution.height}")
            print(f"FPS: {project.model.project.fps}")
            print(f"Estimated frames: {timeline.total_frames}")
            if args.command == "info":
                print(f"Narration: {project.model.audio.narration or 'none'}")
                print(f"Output: {output_root(project.source)}")
            return 0
        if args.command in {"render", "render-scene"}:
            result = Director().render(project, workers=args.workers, resume=args.resume, force=args.force, preview=args.preview,
                from_seconds=getattr(args, "from_seconds", None), to_seconds=getattr(args, "to_seconds", None),
                scene_id=getattr(args, "scene_id", None), dedupe=not args.no_dedupe)
            print(f"Frames ready: {result.frames_dir} (rendered {result.rendered}, reused {result.reused})"); return 0
        if args.command == "encode":
            output = FFmpegEngine().encode(project, preview=args.preview); print(f"Video created: {output}"); return 0
        if args.command == "contact-sheet":
            output = create_contact_sheet(project); print(f"Contact sheet created: {output}"); return 0
        if args.command == "clean":
            target = output_root(project.source)
            if target.exists(): shutil.rmtree(target)
            print(f"Removed output: {target}"); return 0
    except (ProjectError, RuntimeError, ValueError, CommandError) as exc:
        logging.error("%s", exc)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
