"""Copy the single-source library and examples into the Claude skill folder, and optionally build the .skill zip.

    python tools/sync_skill.py            # sync only
    python tools/sync_skill.py --build    # sync, then write dist/stickman-animation.skill
"""
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skill" / "stickman-animation"


def sync():
    scripts = SKILL / "scripts"
    scripts.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / "src" / "stickman_anim" / "lib.py", scripts / "stickman_lib.py")
    shutil.copyfile(ROOT / "src" / "stickman_anim" / "examples" / "pr_review.py", scripts / "example_demo.py")


def build():
    out = ROOT / "dist"
    out.mkdir(exist_ok=True)
    target = out / "stickman-animation.skill"
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(SKILL.rglob("*")):
            if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc":
                z.write(p, Path("stickman-animation") / p.relative_to(SKILL))
    return target


if __name__ == "__main__":
    sync()
    print("synced skill scripts")
    if "--build" in sys.argv:
        print("built", build())
