"""Phase B Character Rigging, IK, Lip-Sync, and Crowds Demo.

Demonstrates:
- 2-bone IK limbs with natural joint bending.
- Named procedural actions: walking, waving, pointing, celebrating.
- Character archetypes: Human with accessories, Robot with eye look-at and mouth lip-sync.
- Speech and thought bubbles, emotes (!, heart, ?).
- Background celebrating crowd.
"""
import math
from stickman_anim import *

N = 30


def render(f):
    c = Frame(f)
    t = float(f)

    # Background texture
    c.background("dark")
    c.floor(310)

    # 1. Celebrating crowd in background
    c.crowd((420, 230, 200, 80), count=5, action="celebrate", t=t)

    # 2. Walking Human with hat and coffee
    walk_x = 80.0 + (t % 30) * 4.0
    c.character(
        walk_x, 310,
        kind="human",
        scale=1.0,
        facing="right",
        action="walk",
        t=t,
        accessories=["hat", "glasses"],
        props={"right": "coffee"}
    )
    if (f // 8) % 2 == 0:
        c.emote((walk_x, 215), kind="!")

    # 3. Robot agent explaining with pointer and lip-sync
    target_point = (walk_x, 240)
    mouth_vol = 0.5 + 0.5 * math.sin(t * 0.8)
    c.character(
        340, 310,
        kind="robot",
        scale=1.1,
        facing="left",
        action="point",
        t=t,
        look_at=target_point,
        mouth_open=mouth_vol,
        accessories=["headphones"]
    )

    # 4. Speech and thought bubbles
    c.speech_bubble((340, 205), "IK Rig active!", thought=False, progress=1.0)

    # 5. Title
    c.text((320, 32), "Phase B: Articulated Characters & Rigging", font(18), WHITE, "mm")

    return c.image()


if __name__ == "__main__":
    main(render, N, "character_rig_demo", [0, 8, 16, 24])
