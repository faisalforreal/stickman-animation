import os
import shutil

import pytest

FORMAT_SIZES = {"gif": (640, 360), "gif-hd": (1280, 720), "video-hd": (1920, 1080), "video-4k": (3840, 2160)}


@pytest.mark.parametrize("fmt,size", FORMAT_SIZES.items())
def test_frame_size_follows_format_flag(py, fmt, size):
    r = py("import stickman_anim as s; print(s.Frame(0).image().size, s.FORMAT)", fmt)
    assert r.returncode == 0, r.stderr
    assert str(size) in r.stdout and fmt in r.stdout


def test_theme_colours(py):
    dark = py("import stickman_anim as s; print(s.BG, s.WHITE)", "bg-black").stdout
    light = py("import stickman_anim as s; print(s.BG, s.WHITE)", "bg-white").stdout
    assert dark.startswith("(0, 0, 0)")
    assert light.startswith("(255, 255, 255)")
    assert dark != light


def test_light_theme_frame_is_mostly_white(py):
    r = py("import stickman_anim as s\nim=s.Frame(3).image()\nc=s.Frame(3); c.robot(100,300)\n"
           "im=c.image().convert('L'); print(sum(im.getdata())/ (im.width*im.height))", "gif bg-white")
    assert float(r.stdout) > 230


def test_frames_are_deterministic(py):
    code = ("import stickman_anim as s, hashlib\n"
            "def mk(f):\n c=s.Frame(f); c.robot(100,300); c.text((50,50),'hi',s.font(12),s.WHITE); return c.image()\n"
            "print(hashlib.md5(mk(7).tobytes()).hexdigest()); print(hashlib.md5(mk(7).tobytes()).hexdigest())")
    a, b = py(code, "gif").stdout.split()
    assert a == b


def test_workers_give_identical_frames(py):
    code = ("import stickman_anim as s, hashlib\n"
            "def render(f):\n c=s.Frame(f); c.human(60+f*10,300); return c.image()\n"
            "h=lambda w:[hashlib.md5(i.tobytes()).hexdigest() for i in s.iter_frames(render,6,w)]\n"
            "print(h(1)==h(2))")
    r = py(code, "gif")
    assert r.stdout.strip() == "True", r.stderr


def test_export_gif(py, tmp_path):
    code = ("import stickman_anim as s\n"
            "def render(f):\n c=s.Frame(f); c.robot(60+f*20,300); return c.image()\n"
            "print(s.export(render, 5, r'%s/t'))" % tmp_path)
    r = py(code, "gif bg-white")
    assert r.returncode == 0, r.stderr
    from PIL import Image
    im = Image.open(str(tmp_path / "t.gif"))
    assert im.size == (640, 360) and im.n_frames == 5


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg not installed")
def test_export_mp4(py, tmp_path):
    code = ("import stickman_anim as s\n"
            "def render(f):\n c=s.Frame(f); c.robot(60+f*20,300); return c.image()\n"
            "print(s.export(render, 5, r'%s/v', loops=2))" % tmp_path)
    r = py(code, "video-hd")
    assert r.returncode == 0, r.stderr
    p = tmp_path / "v.mp4"
    assert p.exists() and p.stat().st_size > 1000
    import subprocess
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=width,height", "-of", "csv=p=0",
                          str(p)], capture_output=True, text=True).stdout.strip()
    assert out == "1920,1080"


def test_contact_sheet_stays_small(py, tmp_path):
    code = ("import stickman_anim as s\n"
            "def render(f):\n c=s.Frame(f); c.robot(60,300); return c.image()\n"
            "s.sheet(render,[0,1,2,3], r'%s/sheet.png')" % tmp_path)
    assert py(code, "video-4k").returncode == 0
    from PIL import Image
    assert Image.open(str(tmp_path / "sheet.png")).size == (1280, 720)       # 2 cols x 640 wide tiles
