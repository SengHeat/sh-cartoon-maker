import wave

from cartoon_studio.engine.lipsync_engine import SubtitleCue, amplitude_mouth_states, export_srt


def test_amplitude_states_are_deterministic(tmp_path):
    wav = tmp_path / "voice.wav"
    samples = ([0] * 100 + [3000] * 100 + [16000] * 100)
    with wave.open(str(wav), "wb") as stream:
        stream.setparams((1, 2, 300, 300, "NONE", "none"))
        stream.writeframes(b"".join(value.to_bytes(2, "little", signed=True) for value in samples))
    assert amplitude_mouth_states(wav, fps=3) == ("closed", "small", "wide")
    assert amplitude_mouth_states(wav, fps=3) == amplitude_mouth_states(wav, fps=3)


def test_khmer_srt_is_utf8_and_timed(tmp_path):
    target = export_srt([SubtitleCue(0, 1.25, "សួស្តី ពិភពលោក")], tmp_path / "khmer.srt")
    assert target.read_text(encoding="utf-8") == "1\n00:00:00,000 --> 00:00:01,250\nសួស្តី ពិភពលោក\n"
