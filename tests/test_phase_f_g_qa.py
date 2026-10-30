import os
import tempfile
import pytest
from stickman_anim import *
from stickman_anim.qa import lint_storyboard, search_assets
from stickman_anim.storyboard import render_storyboard
from stickman_anim.captions import ChunkItem, WordItem, export_srt, export_vtt


def test_self_qa_linter_checks():
    # 1. Off-canvas element
    bad_spec_offcanvas = {
        "aspect": "16:9",
        "scenes": [{
            "name": "bad_scene",
            "frames": 20,
            "elements": [{"type": "mockup", "box": [-50, 50, 200, 100]}]
        }]
    }
    rep1 = lint_storyboard(bad_spec_offcanvas)
    assert not rep1.passed
    assert any(i.code == "OFF_CANVAS" for i in rep1.issues)

    # 2. Caption collision
    bad_spec_collision = {
        "aspect": "16:9",
        "scenes": [{
            "name": "collision_scene",
            "frames": 20,
            "narration": "This is talking with captions.",
            "elements": [{"type": "mockup", "box": [100, 260, 200, 80]}]  # bottom Y=340 > caption safe limit
        }]
    }
    rep2 = lint_storyboard(bad_spec_collision)
    assert any(i.code == "CAPTION_COLLISION" for i in rep2.issues)

    # 3. Clean valid storyboard
    clean_spec = {
        "aspect": "16:9",
        "scenes": [{
            "name": "clean_scene",
            "frames": 20,
            "background": "dark",
            "narration": "Clean test scene.",
            "elements": [
                {"type": "character", "cx": 200, "floor_y": 240, "kind": "human"},
                {"type": "icon", "name": "rocket", "pos": [450, 100], "size": 36}
            ]
        }]
    }
    rep3 = lint_storyboard(clean_spec)
    assert rep3.passed


def test_searchable_asset_index():
    res_bot = search_assets("robot")
    assert "archetypes" in res_bot or "icons" in res_bot

    res_walk = search_assets("walk")
    assert "poses" in res_walk
    assert "walk" in res_walk["poses"]

    res_coffee = search_assets("coffee")
    assert "icons" in res_coffee
    assert "coffee" in res_coffee["icons"]


def test_sidecar_srt_and_vtt_export():
    temp_dir = tempfile.mkdtemp()
    chunks = [
        ChunkItem(start=1.0, end=2.5, words=[WordItem("Hello", 1.0, 1.8), WordItem("world", 1.8, 2.5)]),
        ChunkItem(start=3.0, end=4.2, words=[WordItem("Next", 3.0, 3.5), WordItem("step", 3.5, 4.2)])
    ]

    srt_path = os.path.join(temp_dir, "subs.srt")
    export_srt(chunks, srt_path)
    assert os.path.isfile(srt_path)
    with open(srt_path, "r", encoding="utf-8") as f:
        srt_content = f.read()
    assert "1\n00:00:01,000 --> 00:00:02,500\nHello world" in srt_content

    vtt_path = os.path.join(temp_dir, "subs.vtt")
    export_vtt(chunks, vtt_path)
    assert os.path.isfile(vtt_path)
    with open(vtt_path, "r", encoding="utf-8") as f:
        vtt_content = f.read()
    assert "WEBVTT" in vtt_content
    assert "00:00:01.000 --> 00:00:02.500" in vtt_content


def test_storyboard_runner():
    temp_dir = tempfile.mkdtemp()
    out_mp4 = os.path.join(temp_dir, "storyboard_test.mp4")

    spec = {
        "title": "Storyboard Test",
        "aspect": "16:9",
        "ms": 120,
        "scenes": [
            {
                "name": "intro",
                "frames": 10,
                "background": "dark",
                "elements": [
                    {"type": "character", "cx": 240, "floor_y": 310, "kind": "robot", "action": "wave"},
                    {"type": "icon", "name": "sparkles", "pos": [380, 150], "size": 32},
                    {"type": "text", "pos": [320, 40], "text": "Declarative Storyboard"}
                ]
            }
        ]
    }
    res = render_storyboard(spec, output_path=out_mp4, lint=True)
    assert os.path.isfile(res)
    assert os.path.getsize(res) > 1000
