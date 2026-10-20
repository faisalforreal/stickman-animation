import os

from conftest import ROOT


def read(*p):
    with open(os.path.join(ROOT, *p), encoding="utf-8") as f:
        return f.read()


def test_skill_copy_matches_source():
    assert read("src", "stickman_anim", "lib.py") == read("skill", "stickman-animation", "scripts", "stickman_lib.py"), \
        "run: python tools/sync_skill.py"
    assert read("src", "stickman_anim", "examples", "pr_review.py") == \
        read("skill", "stickman-animation", "scripts", "example_demo.py"), "run: python tools/sync_skill.py"


def test_skill_has_valid_frontmatter():
    text = read("skill", "stickman-animation", "SKILL.md")
    head = text.split("---")[1]
    assert "name: stickman-animation" in head and "description:" in head
