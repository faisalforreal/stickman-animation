import math
import pytest
from stickman_anim import *
from stickman_anim.rig import (
    solve_2bone_ik, get_action_pose, Character, draw_emote, draw_speech_bubble, draw_crowd
)


def test_2bone_ik_solver():
    root = (100.0, 100.0)
    target = (130.0, 100.0)
    l1, l2 = 20.0, 20.0

    # Normal reach
    mid = solve_2bone_ik(root, target, l1, l2, bend_dir=1)
    d1 = math.hypot(mid[0] - root[0], mid[1] - root[1])
    d2 = math.hypot(target[0] - mid[0], target[1] - mid[1])
    assert abs(d1 - l1) < 1e-2
    assert abs(d2 - l2) < 1e-2
    assert mid[1] > root[1]  # Bends downward with bend_dir=1

    # Overextended / unreachable target (target distance 50 > l1 + l2 40)
    far_target = (150.0, 100.0)
    mid_far = solve_2bone_ik(root, far_target, l1, l2, bend_dir=1)
    d_far = math.hypot(mid_far[0] - root[0], mid_far[1] - root[1])
    assert abs(d_far - l1) < 1e-2


def test_named_poses_and_actions():
    actions = ["walk", "run", "wave", "point", "type", "sit", "shrug", "jump", "celebrate", "fail", "hold", "hand_off", "think"]
    for act in actions:
        pose = get_action_pose(act, t=5.0, facing="right")
        assert pose is not None
        assert isinstance(pose.torso_tilt, (int, float))
        assert isinstance(pose.head_tilt, (int, float))


def test_character_archetypes_and_accessories():
    c = Frame(0)
    # Human with accessories and prop
    h = c.character(120, 300, kind="human", action="wave", t=3.0, accessories=["glasses", "hat"], props={"right": "coffee"})
    assert h.kind == "human"

    # Robot with look-at and lip sync
    r = c.character(240, 300, kind="robot", action="point", look_at=(300, 100), mouth_open=0.8, accessories=["headphones"])
    assert r.kind == "robot"

    # Server bot
    s = c.character(360, 300, kind="server_bot", action="idle")
    assert s.kind == "server_bot"

    # Emotes and speech bubbles
    c.emote((120, 210), kind="!")
    c.emote((240, 210), kind="heart")
    c.speech_bubble((120, 220), "Ready!", thought=False, progress=1.0)
    c.speech_bubble((240, 220), "Thinking...", thought=True, progress=1.0)

    # Crowd
    c.crowd((400, 200, 220, 100), count=4, action="celebrate", t=2.0)

    img = c.image()
    assert img.size == (1280, 720)
