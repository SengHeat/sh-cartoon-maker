from __future__ import annotations

import json
import shutil
import subprocess
import wave

import pytest
from PIL import Image

from cartoon_studio.config import load_project
from cartoon_studio.engine.director import Director
from cartoon_studio.engine.ffmpeg_engine import FFmpegEngine


@pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"), reason="FFmpeg tools unavailable")
def test_encoded_preview_contains_audio_stream(tmp_path, monkeypatch):
    assets = tmp_path / "assets"; assets.mkdir()
    Image.new("RGB", (64, 36), "navy").save(assets / "bg.png")
    with wave.open(str(assets / "voice.wav"), "wb") as stream:
        stream.setparams((1, 2, 8000, 8000, "NONE", "none"))
        stream.writeframes(b"\0\0" * 8000)
    story = tmp_path / "story.json"
    story.write_text(json.dumps({
        "format_version": 1,
        "project": {"title": "Audio", "mode": "2.5d", "resolution": {"width": 64, "height": 36}, "fps": 4, "timing_mode": "scenes_driven"},
        "audio": {"narration": "assets/voice.wav"},
        "scenes": [{"id": "one", "duration": 1, "background": {"source": "assets/bg.png"}}],
    }), encoding="utf-8")
    monkeypatch.setenv("CARTOON_STUDIO_OUTPUT", str(tmp_path / "out"))
    project = load_project(story)
    Director().render(project, preview=True, workers=1, force=True)
    video = FFmpegEngine().encode(project, preview=True)
    result = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=codec_name", "-of", "csv=p=0", str(video)], capture_output=True, text=True, check=True)
    assert result.stdout.strip() == "aac"
    video_probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "stream=codec_name", "-of", "csv=p=0", str(video)], capture_output=True, text=True, check=True)
    assert video_probe.stdout.strip() == "h264"
