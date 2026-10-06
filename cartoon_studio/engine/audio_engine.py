from __future__ import annotations

from dataclasses import dataclass

from cartoon_studio.config import LoadedProject


@dataclass(frozen=True)
class MixClip:
    source: str
    start: float
    volume: float
    loop: bool
    fade_in: float
    fade_out: float


class AudioEngine:
    @staticmethod
    def clips(project: LoadedProject) -> list[MixClip]:
        model = project.model
        clips: list[MixClip] = []
        if model.audio.narration:
            clips.append(MixClip(model.audio.narration, 0, model.defaults.narration_volume, False, 0, 0))
        if model.audio.background_music:
            clips.append(MixClip(model.audio.background_music, 0, model.defaults.music_volume, True, 1, 1))
        scene_start = 0.0
        for scene, duration in zip(model.scenes, project.scene_durations, strict=True):
            for character in scene.characters:
                if character.dialogue_audio:
                    clips.append(MixClip(character.dialogue_audio, scene_start, model.defaults.narration_volume, False, 0, 0))
            for clip in scene.audio:
                clips.append(MixClip(clip.source, scene_start + clip.start, clip.volume, clip.loop, clip.fade_in, clip.fade_out))
            scene_start += duration
        return clips
