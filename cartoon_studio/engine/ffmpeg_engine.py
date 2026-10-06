from __future__ import annotations

import shutil
from pathlib import Path

from cartoon_studio.config import LoadedProject
from cartoon_studio.engine.audio_engine import AudioEngine
from cartoon_studio.utils.paths import output_root
from cartoon_studio.utils.subprocess import CommandError, run_checked


class FFmpegEngine:
    """Encode the recovery-safe PNG sequence, optionally with a mixed audio bed."""

    def __init__(self, executable: str = "ffmpeg") -> None:
        self.executable = executable

    def encode(self, project: LoadedProject, *, preview: bool = False) -> Path:
        if not shutil.which(self.executable):
            raise CommandError(f"FFmpeg executable not found: {self.executable}")
        root = output_root(project.source)
        frames = root / "frames" / "frame_%06d.png"
        if not (root / "frames" / "frame_000001.png").is_file():
            raise CommandError(f"No rendered frames found in {root / 'frames'}")
        output = root / "final.mp4"
        fps = min(12, project.model.project.fps) if preview else project.model.project.fps
        command = [self.executable, "-y", "-framerate", str(fps), "-start_number", "1", "-i", str(frames)]
        clips = AudioEngine.clips(project)
        # A single narration/dialogue track needs no filter graph and covers the
        # canonical workflow. Multi-track mixing is added deterministically below.
        for clip in clips:
            command.extend(["-stream_loop", "-1" if clip.loop else "0", "-i", str(project.resolve(clip.source))])
        if clips:
            filters: list[str] = []
            labels: list[str] = []
            for index, clip in enumerate(clips, 1):
                delay = round(clip.start * 1000)
                label = f"a{index}"
                filters.append(f"[{index}:a]volume={clip.volume},adelay={delay}|{delay}[{label}]")
                labels.append(f"[{label}]")
            filters.append(f"{''.join(labels)}amix=inputs={len(labels)}:duration=longest:normalize=0[aout]")
            command.extend(["-filter_complex", ";".join(filters), "-map", "0:v:0", "-map", "[aout]"])
        command.extend(["-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart"])
        if clips:
            command.extend(["-c:a", "aac", "-shortest"])
        command.append(str(output))
        run_checked(command)
        return output
