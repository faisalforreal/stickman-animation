"""A robot agent opens a pull request and a human approves it (the minimal worked example).

Standard structure: timeline constants -> render(f) -> main().
Run:  stickman demo pr_review [gif|gif-hd|video-hd|video-4k] [bg-black|bg-white]
"""
try:
    from stickman_anim import *  # noqa: F401,F403
except ImportError:              # running inside the Claude skill, next to stickman_lib.py
    import os
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from stickman_lib import *  # noqa: F401,F403

N = 56
T_TYPE, T_SEND, T_REVIEW, T_APPROVE = 0, 12, 20, 38     # frame numbers where each phase begins
FL = 322


def render(f):
    c = Frame(f)
    c.floor(FL)
    title = font(18)
    small = font(11)

    # title types in over the first 8 frames
    c.typed((320, 34), "Agent opens a PR, human approves", title, WHITE, clamp((f + 1) / 8.0), "mm", cursor=False)

    # --- agent on the left
    typing = f < T_SEND
    c.robot(70, FL, eye=GREEN if f >= T_APPROVE + 6 else CYAN,
            hr=(118, 250 - c.wig) if typing else None, cheer=f >= T_APPROVE + 6)
    c.text((70, 340), "AI Agent", small, GREY, "mm")

    # --- review window in the middle
    c.window((190, 110), (450, 280), "Pull Request #42", small)
    for i, lab in enumerate(["Tests pass", "Logic OK", "Secure"]):
        y = 160 + i * 34
        a = T_REVIEW + i * 5
        c.text((240, y), lab, small, WHITE if f >= a else GREY)
        if f < a:
            c.circle((214, y), 7, DIM, 2)
        elif f < a + 4:
            c.spinner((214, y), 7)
        else:
            c.circle((214, y), 7, GREEN, 2)
            c.check((214, y), 9, GREEN, 2.2)
    if f >= T_APPROVE:
        c.rect((330, 248), (434, 270), GREEN, 2.4, 0.6)
        c.text((382, 259), "Approved", small, GREEN, "mm")

    # --- PR packet flying agent -> window
    if T_SEND <= f < T_SEND + 8:
        c.packet(arc_lerp((110, 235), (190, 190), (f - T_SEND + 1) / 8.0, 20), CYAN)

    # --- human on the right
    done = f >= T_APPROVE + 6
    c.human(560, FL, thumbs_up=done, smile=done)
    c.text((560, 340), "Human", small, GREY, "mm")
    if T_REVIEW <= f < T_APPROVE:                       # thinking dots
        for q in range(3):
            if q <= f % 3:
                c.circle((550 + q * 9, 205), 1.8, CYAN, fill=True)

    if done:
        for k, p in enumerate([(40, 120), (610, 110), (300, 70)]):
            if (f + k) % 3 == 0:
                c.sparkle(p)
    return c.image()


if __name__ == "__main__":
    main(render, N, "pr_review", [6, 16, 28, 46])
