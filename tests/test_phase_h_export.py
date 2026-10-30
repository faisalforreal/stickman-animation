import os
import tempfile
import pytest
from PIL import Image, ImageDraw
from stickman_anim import *
from stickman_anim.paths import Path
from stickman_anim.exporters import (
    SOCIAL_PRESETS, export_animated_svg, generate_thumbnail
)


def test_social_presets():
    assert "youtube" in SOCIAL_PRESETS
    assert "shorts" in SOCIAL_PRESETS
    assert "reels" in SOCIAL_PRESETS
    assert "x" in SOCIAL_PRESETS
    assert "linkedin" in SOCIAL_PRESETS

    assert SOCIAL_PRESETS["youtube"]["size"] == (1920, 1080)
    assert SOCIAL_PRESETS["shorts"]["size"] == (1080, 1920)
    assert SOCIAL_PRESETS["linkedin"]["size"] == (1080, 1080)


def test_animated_svg_export():
    p1 = Path().move_to(20, 20).line_to(100, 20).line_to(100, 100).close()
    p2 = Path().move_to(120, 20).line_to(200, 100)

    temp_dir = tempfile.mkdtemp()
    out_svg = os.path.join(temp_dir, "anim.svg")
    actual = export_animated_svg([p1, p2], out_svg, width=640, height=360, duration_sec=2.5)

    assert os.path.isfile(actual)
    with open(actual, "r", encoding="utf-8") as f:
        content = f.read()
    assert "<svg" in content
    assert "@keyframes drawStroke" in content
    assert 'class="hand-path"' in content


def test_auto_thumbnail_generator():
    temp_dir = tempfile.mkdtemp()
    # Blank frame vs complex frame
    im_blank = Image.new("RGB", (640, 360), (0, 0, 0))
    im_rich = Image.new("RGB", (640, 360), (0, 0, 0))
    d = ImageDraw.Draw(im_rich)
    for i in range(20):
        d.line([(i * 30, 0), (640 - i * 30, 360)], fill=(255, 255, 255), width=3)

    out_thumb = os.path.join(temp_dir, "thumb.png")
    actual = generate_thumbnail([im_blank, im_rich], out_thumb, title_badge="Top Scene")

    assert os.path.isfile(actual)
    im_res = Image.open(actual)
    assert im_res.size == (640, 360)
