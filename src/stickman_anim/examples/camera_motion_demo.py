"""Phase C Motion, Easing, Particles & Virtual Camera Demo.

Demonstrates:
- Virtual camera panning, zooming, and camera rumble shake.
- Multi-plane parallax (distant mountains/grid move slower than foreground).
- Stop-motion particles: sparks, confetti, and comic speed lines.
- Spring and squash-and-stretch motion.
"""
import math
from stickman_anim import *
from stickman_anim.motion import Camera, Track, ease_out_back, squash_stretch

N = 36


def render(f):
    c = Frame(f)
    t = f / float(N)

    # 1. Camera track: zoom in and rumble when landing
    cam = Camera(cx=320.0, cy=180.0, zoom=1.0)
    if f < 18:
        # Camera pans right following agent
        cam_x = 320.0 + (f / 18.0) * 60.0
        cam.look_at(cam_x, 180.0, zoom=1.0 + (f / 18.0) * 0.25)
    else:
        # Landing impact shake
        shake_intensity = max(0.0, 1.0 - (f - 18) / 12.0)
        cam.look_at(380.0, 180.0, zoom=1.25)
        cam.add_shake(amplitude=5.0 * shake_intensity)

    # 2. Far Background with Parallax (z = 0.3)
    p_bg1 = cam.world_to_screen((100, 120), z=0.3, t=t)
    p_bg2 = cam.world_to_screen((540, 120), z=0.3, t=t)
    c.line(p_bg1, p_bg2, col=(60, 60, 75), w=2.0)

    # 3. Main Stage (z = 1.0)
    fl_pt = cam.world_to_screen((320, 310), z=1.0, t=t)
    c.line((0, fl_pt[1]), (640, fl_pt[1]), col=(120, 120, 130), w=2.0)

    # Character Jump / Squash / Action
    if f < 18:
        # Mid-air jump
        jump_y = 310.0 - math.sin((f / 18.0) * math.pi) * 80.0
        pos = cam.world_to_screen((280.0 + f * 5.0, jump_y), z=1.0, t=t)
        c.character(pos[0], pos[1], kind="human", action="jump", scale=1.0, t=f)
        c.speed_lines(direction="down", intensity=0.7)
    else:
        # Landed with squash-and-stretch
        land_phase = (f - 18) / 18.0
        sx, sy = squash_stretch(land_phase * 2.0, intensity=0.35)
        pos = cam.world_to_screen((370.0, 310.0), z=1.0, t=t)
        c.character(pos[0], pos[1], kind="robot", action="celebrate", scale=1.0 * sy, t=f, accessories=["crown"])

        # Burst of sparks and confetti on impact
        impact_t = (f - 18) * 0.08
        c.sparks(pos, t=impact_t, count=20)
        c.confetti((pos[0], pos[1] - 40), t=impact_t, count=25)
        c.emote((pos[0], pos[1] - 80), kind="!")

    # 4. Title (HUD layer, no camera transform)
    c.text((320, 32), "Phase C: Motion, Camera & Particles", font(18), WHITE, "mm")

    return c.image()


if __name__ == "__main__":
    main(render, N, "camera_motion_demo", [0, 9, 18, 27])
