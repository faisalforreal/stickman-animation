import os
import subprocess
import sys

import pytest

from conftest import SRC


def cli(*args, cwd=None):
    env = dict(os.environ, PYTHONPATH=SRC)
    env.pop("STICKMAN_FLAGS", None)
    return subprocess.run([sys.executable, "-I", "-m", "stickman_anim", *args], env=env, cwd=cwd,
                          capture_output=True, text=True, timeout=600)


def test_version_and_flags():
    assert cli("version").stdout.strip() == "0.2.0"
    out = cli("flags").stdout
    for word in ("gif-hd", "video-4k", "bg-white"):
        assert word in out


def test_unknown_command_fails():
    assert cli("nope").returncode == 2


@pytest.mark.parametrize("name", ["pr_review", "fewer_devs", "ci_pipeline"])
def test_examples_render_first_frames(py, name):
    code = ("import importlib; m=importlib.import_module('stickman_anim.examples.%s');"
            "im=m.render(m.N-1); im2=m.render(m.N//2); print(im.size)" % name)
    r = py(code, "gif bg-white")
    assert r.returncode == 0, r.stderr
    assert "(640, 360)" in r.stdout


def test_demo_command_writes_gif(tmp_path):
    r = cli("demo", "pr_review", "gif", cwd=str(tmp_path))
    assert r.returncode == 0, r.stderr
    assert (tmp_path / "pr_review.gif").exists()
    assert (tmp_path / "pr_review_sheet.png").exists()


def test_render_command_runs_user_script(tmp_path):
    script = tmp_path / "scene.py"
    script.write_text("from stickman_anim import *\n"
                      "def render(f):\n    c=Frame(f); c.human(100,300); return c.image()\n"
                      "if __name__=='__main__':\n    main(render, 4, 'scene')\n")
    r = cli("render", str(script), "gif", "bg-white", cwd=str(tmp_path))
    assert r.returncode == 0, r.stderr
    assert (tmp_path / "scene.gif").exists()
