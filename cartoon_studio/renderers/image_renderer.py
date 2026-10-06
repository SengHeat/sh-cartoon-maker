from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageEnhance

from cartoon_studio.config import LoadedProject
from cartoon_studio.engine.camera_engine import CameraEngine, CameraState
from cartoon_studio.engine.character_engine import CharacterEngine, CharacterState
from cartoon_studio.engine.compositor import AssetManager, paste_centered, scaled
from cartoon_studio.engine.effect_engine import EffectEngine
from cartoon_studio.engine.parallax_engine import ParallaxEngine
from cartoon_studio.engine.rig_engine import RigEngine
from cartoon_studio.engine.sprite_engine import SpriteAnimationEngine
from cartoon_studio.engine.timeline import Timeline
from cartoon_studio.models import Scene
from cartoon_studio.utils.hashing import stable_hash
from cartoon_studio.utils.interpolation import clamp
from .base import BaseRenderer


@dataclass(frozen=True)
class RenderContext:
    frame: int
    scene_index: int
    progress: float
    local_seconds: float
    width: int
    height: int
    fps: int


class ImageRenderer(BaseRenderer):
    def __init__(self, width: int | None = None, height: int | None = None, fps: int | None = None):
        self.override = (width, height, fps)
        self.project: LoadedProject | None = None
        self.timeline: Timeline | None = None
        self.assets = AssetManager()
        self.rigs = RigEngine(self.assets)
        self.sprites = SpriteAnimationEngine()

    def prepare(self, project: LoadedProject) -> None:
        self.project = project
        self.timeline = Timeline(project, self.override[2])

    @property
    def size(self) -> tuple[int, int]:
        assert self.project
        resolution = self.project.model.project.resolution
        return self.override[0] or resolution.width, self.override[1] or resolution.height

    def context(self, frame: int) -> RenderContext:
        assert self.timeline
        timeline_scene = self.timeline.scene_at_frame(frame)
        return RenderContext(frame, timeline_scene.index, self.timeline.local_progress(frame), self.timeline.local_scene_time(frame), *self.size, self.timeline.fps)

    def _states(self, scene: Scene, context: RenderContext) -> tuple[CameraState, dict[str, CharacterState]]:
        assert self.project
        settings = self.project.model
        camera = CameraEngine.state(scene.camera, context.progress, settings.defaults.camera_easing, context.frame, settings.project.seed)
        characters = {c.layer_id: CharacterEngine.state(c, context.local_seconds, context.progress) for c in scene.characters}
        return camera, characters

    def signature(self, frame: int) -> str:
        assert self.project
        context = self.context(frame)
        scene = self.project.model.scenes[context.scene_index]
        camera, characters = self._states(scene, context)
        animated_effects = {"fog", "film_grain", "flash", "fade", "shake"}
        payload = {
            "scene": scene.id,
            "camera": camera,
            "characters": characters,
            "effects": [(e.type, e.intensity, e.speed, context.frame if e.type in animated_effects else None) for e in scene.effects],
            "transition": (scene.transition_out.type, round(context.progress, 6)) if scene.transition_out.type != "cut" else None,
            "size": self.size,
            "seed": self.project.model.project.seed,
        }
        dynamic_actions = {"subtle_breathing", "walk_in_place", "walk", "run", "nod", "shake", "wave", "float", "fade_in", "fade_out", "stand", "fall", "take"}
        for character in scene.characters:
            layer = next((item for item in scene.layers if item.id == character.layer_id), None)
            if not layer: continue
            source = self.project.resolve(layer.source)
            has_rig = (source.parent / "rig.json").is_file()
            has_cycle = self.sprites.has_animation(source, character.action)
            if has_cycle or character.dialogue_audio or (has_rig and (character.auto_blink or character.action in dynamic_actions or character.motion is not None)):
                payload.setdefault("animated_characters", []).append((character.layer_id, frame))
        return stable_hash(payload)

    def render_frame(self, frame: int) -> Image.Image:
        assert self.project
        context = self.context(frame)
        scene = self.project.model.scenes[context.scene_index]
        image = self.render_scene(scene, context)
        transition = scene.transition_out
        if transition.type != "cut" and transition.duration > 0:
            remaining = (1 - context.progress) * (self.timeline.scenes[context.scene_index].duration if self.timeline else scene.duration)
            if remaining <= transition.duration:
                mix = clamp(1 - remaining / transition.duration)
                if transition.type == "fade_black" or context.scene_index + 1 >= len(self.project.model.scenes):
                    image = Image.blend(image, Image.new("RGBA", image.size, (0, 0, 0, 255)), mix)
                elif transition.type == "crossfade":
                    next_scene = self.project.model.scenes[context.scene_index + 1]
                    next_context = RenderContext(context.frame, context.scene_index + 1, mix, mix * transition.duration, context.width, context.height, context.fps)
                    image = Image.blend(image, self.render_scene(next_scene, next_context), mix)
        return image.convert("RGB")

    def render_scene(self, scene: Scene, context: RenderContext) -> Image.Image:
        assert self.project
        width, height = context.width, context.height
        camera, character_states = self._states(scene, context)
        canvas = Image.new("RGBA", (width, height), self.project.model.project.background_color)
        background = self.assets.get_image(self.project.resolve(scene.background.source))
        bg = scaled(background, scene.background.scale, (width, height), camera.zoom)
        bx = width / 2 + (0.5 - camera.x) * max(width, bg.width)
        by = height / 2 + (0.5 - camera.y) * max(height, bg.height)
        paste_centered(canvas, bg, bx, by)
        for layer in sorted(scene.layers, key=lambda item: item.depth):
            source_path = self.project.resolve(layer.source)
            character = next((item for item in scene.characters if item.layer_id == layer.id), None)
            rig_path = source_path.parent / "rig.json"
            animated_sprite = self.sprites.frame(source_path, character.action, context.local_seconds) if character else None
            if character and rig_path.is_file():
                dialogue = self.project.resolve(character.dialogue_audio) if character.dialogue_audio else None
                source = self.rigs.render(rig_path, character, context.local_seconds, context.progress, context.frame, context.fps, self.project.model.project.seed, dialogue)
            elif animated_sprite is not None:
                source = animated_sprite
            else:
                source = self.assets.get_image(source_path)
            state = character_states.get(layer.id, CharacterState())
            layer_scale = layer.scale * camera.zoom * state.scale
            sprite = scaled(source, layer.scale_mode, (width, height), layer_scale)
            if state.rotation:
                sprite = sprite.rotate(state.rotation, Image.Resampling.BICUBIC, expand=True)
            opacity = clamp(layer.opacity * state.opacity)
            if opacity < 1:
                alpha = sprite.getchannel("A").point(lambda value: round(value * opacity))
                sprite.putalpha(alpha)
            px, py = layer.position.x + state.x, layer.position.y + state.y
            parallax = ParallaxEngine.offset(camera.x, camera.y, layer.depth, width, height)
            x = px * width + parallax[0]
            y = py * height + parallax[1]
            anchor = layer.anchor
            anchor_xy = (anchor.x, anchor.y) if anchor else ((0.5, 1.0) if layer.type == "character" else (0.5, 0.5))
            paste_centered(canvas, sprite, x, y, anchor_xy)
        canvas = EffectEngine.apply(canvas, scene.effects, context.frame, context.progress, self.project.model.project.seed)
        shake = next((e.intensity for e in scene.effects if e.type == "shake"), 0.0)
        if shake:
            dx = round(math.sin(context.frame * 2.17) * width * shake * 0.01)
            dy = round(math.cos(context.frame * 1.91) * height * shake * 0.01)
            shifted = Image.new("RGBA", canvas.size, self.project.model.project.background_color)
            shifted.alpha_composite(canvas, (dx, dy)); canvas = shifted
        return canvas

    def finalize(self) -> None:
        pass
