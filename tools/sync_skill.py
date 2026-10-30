"""Copy the single-source library, TTS, and captioning modules into the skill folder, and optionally build the .skill zip.

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
    src = ROOT / "src" / "stickman_anim"
    
    shutil.copyfile(src / "lib.py", scripts / "stickman_lib.py")
    shutil.copyfile(src / "tts.py", scripts / "tts.py")
    shutil.copyfile(src / "captions.py", scripts / "captions.py")
    shutil.copyfile(src / "presets.py", scripts / "presets.py")
    if (src / "capcut_presets.json").is_file():
        shutil.copyfile(src / "capcut_presets.json", scripts / "capcut_presets.json")
    shutil.copyfile(src / "examples" / "pr_review.py", scripts / "example_demo.py")


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
