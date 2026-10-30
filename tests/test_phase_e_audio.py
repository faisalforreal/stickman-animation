import os
import tempfile
import wave
import pytest
from stickman_anim import *
from stickman_anim.audio_fx import (
    parse_cued_script, CueTimeline,
    parse_dialogue_script, get_active_speaker_at,
    synthesize_sfx, calculate_rms_envelope
)


def test_script_cue_parser_and_timeline():
    script = "Welcome to the presentation! @cue(cheer) Today we reveal the universal engine. @cue(rocket) Let's launch!"
    clean_text, cues = parse_cued_script(script)

    # Clean text must not have @cue markers
    assert "@cue" not in clean_text
    assert "Welcome to the presentation!" in clean_text
    assert "Today we reveal the universal engine." in clean_text
    assert len(cues) == 2
    assert cues[0][0] == "cheer"
    assert cues[1][0] == "rocket"
    assert cues[0][1] < cues[1][1]  # Cheer happens before rocket

    # Timeline test
    timeline = CueTimeline(cues, total_frames=100)
    assert timeline.frame_at("cheer") is not None
    assert timeline.frame_at("rocket") is not None
    assert timeline.frame_at("cheer") < timeline.frame_at("rocket")

    f_cheer = timeline.frame_at("cheer")
    assert not timeline.has_fired("cheer", f_cheer - 1)
    assert timeline.has_fired("cheer", f_cheer)
    assert timeline.is_active("cheer", f_cheer, window=5)


def test_dialogue_script_parser():
    dialogue_text = """
    [Speaker: Charon] Hello everyone, welcome to the stream!
    [Speaker: Puck] Glad to be here, Charon. What are we building today?
    Charon: A universal hand-drawn animation engine.
    """
    lines = parse_dialogue_script(dialogue_text)
    assert len(lines) == 3
    assert lines[0][0] == "Charon"
    assert lines[1][0] == "Puck"
    assert lines[2][0] == "Charon"

    intervals = [
        {"speaker": "Charon", "start": 0.0, "end": 2.5},
        {"speaker": "Puck", "start": 2.8, "end": 5.2},
    ]
    assert get_active_speaker_at(intervals, 1.0) == "Charon"
    assert get_active_speaker_at(intervals, 3.5) == "Puck"
    assert get_active_speaker_at(intervals, 2.6) is None  # During pause gap


def test_procedural_sfx_synthesizer():
    temp_dir = tempfile.mkdtemp()
    for sfx_name in ["pop", "click", "whoosh", "ding", "pen_scratch"]:
        out_wav = os.path.join(temp_dir, f"{sfx_name}.wav")
        actual_path = synthesize_sfx(sfx_name, out_wav)
        assert os.path.isfile(actual_path)
        with wave.open(actual_path, "rb") as wf:
            assert wf.getframerate() == 44100
            assert wf.getnchannels() == 1
            assert wf.getnframes() > 100


def test_rms_lip_sync_envelope():
    temp_dir = tempfile.mkdtemp()
    sfx_wav = os.path.join(temp_dir, "ding.wav")
    synthesize_sfx("ding", sfx_wav)

    # Compute 30 frames of amplitude
    envelope = calculate_rms_envelope(sfx_wav, fps=10.0, n_frames=30)
    assert len(envelope) == 30
    assert all(0.0 <= val <= 1.0 for val in envelope)
    # The attack of the chime should have higher amplitude than the tail
    assert envelope[0] > envelope[-1]
