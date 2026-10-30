import os
import pytest
from stickman_anim.tts import load_env, create_mock_tone_wav, get_audio_duration
from stickman_anim.presets import get_preset, list_presets, CURATED_PRESETS
from stickman_anim.captions import estimate_word_timings, chunk_words, build_ass_subtitles


def test_preset_lookup():
    # Curated preset lookup
    p = get_preset("hormozi-bold")
    assert p.name == "hormozi-bold"
    assert p.highlight_color == "#FFE600"
    assert p.pos_y == 75.0

    # MrBeast preset
    mb = get_preset("mrbeast-pop")
    assert mb.highlight_color == "#2BF82A"

    # Default fallback
    unknown = get_preset("non-existent-preset-xyz")
    assert unknown.name == "hormozi-bold"


def test_list_presets():
    all_presets = list_presets()
    assert len(all_presets) >= len(CURATED_PRESETS)
    
    # Filter search
    matches = list_presets(search="hormozi")
    assert any(m["id"] == "hormozi-bold" for m in matches)


def test_timing_and_ass_generation(tmp_path):
    text = "AI agents write code and run tests."
    words = estimate_word_timings(text, total_duration=4.0)
    assert len(words) == len(text.split())
    assert words[0].start >= 0.0
    assert words[-1].end <= 4.0

    chunks = chunk_words(words, max_words_per_chunk=3)
    assert len(chunks) >= 2

    style = get_preset("hormozi-bold")
    ass_text = build_ass_subtitles(chunks, style, play_res_x=1280, play_res_y=720)
    
    assert "[Script Info]" in ass_text
    assert "[V4+ Styles]" in ass_text
    assert "Dialogue:" in ass_text
    # Check 75% Y pos
    assert "\\pos(640.0,540.0)" in ass_text


def test_mock_audio_generation(tmp_path):
    wav_path = str(tmp_path / "mock.wav")
    out = create_mock_tone_wav("Hello test world", wav_path, duration_sec=2.0)
    assert os.path.isfile(out)
    dur = get_audio_duration(out)
    assert 1.8 <= dur <= 2.2
