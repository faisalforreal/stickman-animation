import json
import os
import tempfile
import pytest
from PIL import Image
from stickman_anim import *
from stickman_anim.timeline import Scene, Timeline, run_project_file, ASPECT_PRESETS
from stickman_anim.lib import _detect_video_encoder, iter_frames


def test_aspect_presets_and_safe_zones():
    tl_16_9 = Timeline(aspect="16:9")
    assert tl_16_9.safe_caption_y == 75.0

    tl_9_16 = Timeline(aspect="9:16")
    # In 9:16 vertical video, safe zone must be higher (around 64%) to avoid TikTok/Reels UI
    assert tl_9_16.safe_caption_y == 64.0
    assert tl_9_16.preset["logical"] == (360, 640)

    tl_sq = Timeline(aspect="1:1")
    assert tl_sq.safe_caption_y == 78.0


def test_scene_hash_caching():
    sc1 = Scene(name="intro", frames=20, narration="Welcome", transition_to_next="wipe")
    sc2 = Scene(name="intro", frames=20, narration="Welcome", transition_to_next="wipe")
    sc3 = Scene(name="intro", frames=25, narration="Welcome", transition_to_next="wipe")  # changed frames

    h1 = sc1.compute_hash()
    h2 = sc2.compute_hash()
    h3 = sc3.compute_hash()

    assert h1 == h2
    assert h1 != h3


def test_multithreaded_frame_iteration():
    def simple_render(f):
        c = Frame(f)
        c.circle((f * 10, 50), 5)
        return c.image()

    # Compare single worker vs 2 workers
    f_single = list(iter_frames(simple_render, 8, workers=1))
    f_multi = list(iter_frames(simple_render, 8, workers=2))

    assert len(f_single) == 8
    assert len(f_multi) == 8
    for im1, im2 in zip(f_single, f_multi):
        assert im1.size == im2.size


def test_gpu_encoder_probe():
    enc = _detect_video_encoder()
    assert isinstance(enc, str)
    assert enc in ("libx264", "h264_nvenc", "h264_qsv", "h264_amf", "h264_videotoolbox")


def test_project_json_runner():
    temp_dir = tempfile.mkdtemp()
    proj_path = os.path.join(temp_dir, "test_proj.json")
    out_mp4 = os.path.join(temp_dir, "test_proj.mp4")

    proj_data = {
        "aspect": "16:9",
        "ms": 120,
        "scenes": [
            {"name": "scene1", "frames": 6, "transition": "cut"},
            {"name": "scene2", "frames": 6, "transition": "cut"}
        ]
    }
    with open(proj_path, "w", encoding="utf-8") as f:
        json.dump(proj_data, f)

    res = run_project_file(proj_path, output_path=out_mp4)
    assert os.path.isfile(res)
    assert os.path.getsize(res) > 1000
