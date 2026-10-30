import math
import pytest
from PIL import Image
from stickman_anim import *
from stickman_anim.motion import (
    ease_linear, ease_in_quad, ease_out_quad, ease_in_out_quad,
    ease_in_cubic, ease_out_cubic, ease_in_out_cubic,
    ease_out_back, ease_in_back, ease_out_elastic, ease_out_bounce,
    spring, stagger, squash_stretch, Track, Camera,
    transition_wipe, transition_iris, transition_ink_splash
)


def test_easing_curves_and_spring():
    # Boundary checks
    assert ease_linear(0.0) == 0.0
    assert ease_linear(1.0) == 1.0
    assert ease_out_cubic(0.0) == 0.0
    assert abs(ease_out_cubic(1.0) - 1.0) < 1e-4

    # Back overshoot
    assert ease_out_back(0.7) > 1.0  # Should overshoot 1.0 before settling

    # Bounce
    assert abs(ease_out_bounce(1.0) - 1.0) < 1e-4

    # Spring settles near 1.0 after decay
    assert spring(0.0) == 0.0
    assert abs(spring(2.0, stiffness=100.0, damping=15.0) - 1.0) < 0.05


def test_stagger_and_squash_stretch():
    # 4 items sequenced
    p0 = stagger(0, 4, progress=0.2, overlap=0.5)
    p3 = stagger(3, 4, progress=0.2, overlap=0.5)
    assert p0 > 0.0
    assert p3 == 0.0  # Later item hasn't started yet

    # Squash and stretch volume preservation
    sx, sy = squash_stretch(0.5, intensity=0.2)
    assert abs((sx * sy) - 1.0) < 0.05


def test_keyframe_track():
    # Scalar track
    tr_scalar = Track([(0.0, 10.0), (1.0, 50.0), (2.0, 20.0)])
    assert tr_scalar.at(0.0) == 10.0
    assert tr_scalar.at(2.0) == 20.0
    mid_val = tr_scalar.at(0.5)
    assert 10.0 < mid_val < 50.0

    # 2D Point track
    tr_point = Track([(0.0, (100.0, 100.0)), (1.0, (200.0, 300.0))])
    pt_mid = tr_point.at(0.5)
    assert 100.0 < pt_mid[0] < 200.0
    assert 100.0 < pt_mid[1] < 300.0


def test_virtual_camera_and_parallax():
    cam = Camera(cx=320.0, cy=180.0, zoom=1.0)
    # Origin should be unchanged at center
    center_screen = cam.world_to_screen((320.0, 180.0))
    assert abs(center_screen[0] - 320.0) < 1e-3
    assert abs(center_screen[1] - 180.0) < 1e-3

    # Pan camera right to 400
    cam.look_at(400.0, 180.0)
    screen_pt = cam.world_to_screen((320.0, 180.0), z=1.0)
    assert screen_pt[0] < 320.0  # Stage shifts left when camera looks right

    # Parallax: background moves less than foreground
    bg_pt = cam.world_to_screen((320.0, 180.0), z=0.3)
    fg_pt = cam.world_to_screen((320.0, 180.0), z=1.5)
    assert abs(bg_pt[0] - 320.0) < abs(screen_pt[0] - 320.0)
    assert abs(fg_pt[0] - 320.0) > abs(screen_pt[0] - 320.0)


def test_transitions():
    im1 = Image.new("RGB", (100, 100), (0, 0, 0))
    im2 = Image.new("RGB", (100, 100), (255, 255, 255))

    wipe_half = transition_wipe(im1, im2, 0.5)
    assert wipe_half.size == (100, 100)

    iris_half = transition_iris(im1, im2, 0.5)
    assert iris_half.size == (100, 100)

    splash = transition_ink_splash(im1, im2, 0.5)
    assert splash.size == (100, 100)


def test_frame_motion_and_particles():
    c = Frame(0)
    c.background("dark")
    c.floor(310)

    # Particles
    c.confetti((320, 150), t=0.5, count=10)
    c.sparks((200, 200), t=0.3, count=8)
    c.smoke((150, 280), t=0.4, count=6)
    c.rain((0, 0, 640, 360), t=0.2, count=15)
    c.speed_lines(direction="right", intensity=0.8)

    img = c.image()
    assert img.size == (1280, 720)
