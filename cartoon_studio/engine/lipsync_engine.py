from __future__ import annotations

import array
import wave
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SubtitleCue:
    start: float
    end: float
    text: str


def amplitude_mouth_states(path: str | Path, *, fps: int, duration: float | None = None) -> tuple[str, ...]:
    """Return deterministic closed/small/wide cues; this is not phoneme alignment."""
    with wave.open(str(path), "rb") as stream:
        rate, width = stream.getframerate(), stream.getsampwidth()
        if width not in (1, 2):
            raise ValueError("amplitude lip sync supports 8-bit or 16-bit PCM WAV")
        total = stream.getnframes() if duration is None else min(stream.getnframes(), round(duration * rate))
        raw = stream.readframes(total)
    values = array.array("B" if width == 1 else "h"); values.frombytes(raw)
    samples_per_frame = max(1, round(rate / fps))
    states: list[str] = []
    for start in range(0, len(values), samples_per_frame):
        chunk = values[start:start + samples_per_frame]
        level = sum(abs(v - 128) if width == 1 else abs(v) for v in chunk) / max(1, len(chunk)) / (128 if width == 1 else 32768)
        states.append("wide" if level > .25 else "small" if level > .04 else "closed")
    return tuple(states)


def _timestamp(seconds: float) -> str:
    milliseconds = round(max(0, seconds) * 1000)
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    whole, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{whole:02d},{millis:03d}"


def export_srt(cues: list[SubtitleCue], path: str | Path) -> Path:
    target = Path(path)
    blocks = [f"{index}\n{_timestamp(cue.start)} --> {_timestamp(cue.end)}\n{cue.text}" for index, cue in enumerate(cues, 1)]
    target.write_text("\n\n".join(blocks) + ("\n" if blocks else ""), encoding="utf-8")
    return target
