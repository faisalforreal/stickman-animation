import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")


def run_py(code, flags="", cwd=None):
    """Run python code in a fresh interpreter so the import-time flags take effect."""
    env = dict(os.environ, STICKMAN_FLAGS=flags, PYTHONPATH=SRC)
    r = subprocess.run([sys.executable, "-I", "-c", code], env=env, cwd=cwd,
                       capture_output=True, text=True, timeout=300)
    return r


@pytest.fixture
def py():
    return run_py
