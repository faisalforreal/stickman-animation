"""Companies shrink their developer count: one person works on many projects, AI agents do the rest.

Run:  stickman demo fewer_devs [gif|gif-hd|video-hd|video-4k] [bg-black|bg-white]
"""
try:
    from stickman_anim import *  # noqa: F401,F403
except ImportError:              # running inside the Claude skill, next to stickman_lib.py
    import os
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from stickman_lib import *  # noqa: F401,F403

N = 140
FL = 322
T1, T_CUT, T_MOVE, T2, T_PROJ, T_FIN = 0, 24, 50, 58, 70, 122
XS = [60, 170, 280, 390, 500, 590]
PROJ = [("Project A", 150), ("Project B", 250), ("Project C", 390), ("Project D", 490)]


def render(f):
    c = Frame(f)
    t9, t10, t11, t16 = font(9), font(10), font(11), font(17)
    c.floor(FL)

    # titles
    if f < T2 - 4:
        s = "Companies will shrink their developer count"
        cw = c.tw(s, t16)
        c.typed((320 - cw / 2, 28), s, t16, WHITE, clamp((f + 1) / 18.0), "lm", cursor=False)
    elif f >= T2:
        s = "One person will work on many projects"
        cw = c.tw(s, t16)
        c.typed((320 - cw / 2, 28), s, t16, WHITE, clamp((f - T2 + 1) / 16.0), "lm", cursor=False)

    # developers
    left = 6
    if f < T_MOVE + 6:
        for i, x in enumerate(XS):
            gone = T_CUT + i * 4 if i != 2 else None
            if gone is not None and f >= gone + 5:
                continue
            if i == 2:
                px = x + (320 - x) * clamp((f - T_MOVE) / 8.0)
                c.human(px, FL)
            else:
                c.human(x, FL)
                if gone is not None and f >= gone:
                    c.cross((x, 200), 14, RED, 3)
        left = 6 - sum(1 for i in range(6) if i != 2 and f >= T_CUT + i * 4 + 5)
        c.text((320, 70), "Developers: %d" % left, font(14), WHITE if left > 1 else GREEN, "mm")
    else:
        c.human(320, FL, hl=None, hr=None, thumbs_up=f >= T_FIN, smile=f >= T_FIN)
    c.text((XS[2] if f < T_MOVE else 320, 340), "Developer" if f >= T2 else "", t9, GREY, "mm")

    # projects + agents
    if f >= T_PROJ:
        for i, (name, rx) in enumerate(PROJ):
            s0 = T_PROJ + i * 8
            if f < s0:
                continue
            e0 = s0 + 22
            st = "ok" if f >= e0 else "run"
            c.rect((rx - 46, 66), (rx + 46, 112), GREEN if st == "ok" else CYAN, 2.3, 0.8)
            c.text((rx, 82), name, t11, WHITE, "mm")
            if st == "run":
                c.spinner((rx, 98), 5)
            else:
                c.check((rx, 98), 8, GREEN, 2)
            c.robot(rx, FL, eye=GREEN if st == "ok" else CYAN)
            c.line((rx, 112), (rx, 138), DIM, 1.6, 0.4)
            if s0 <= f < s0 + 6:
                c.packet(arc_lerp((320, 240), (rx, 212), (f - s0 + 1) / 6.0, 20), CYAN)
    if f >= T_PROJ - 8:
        pass

    # caption
    if f >= T_FIN:
        s = "One developer. Many projects. AI agents do the rest."
        cw = c.tw(s, font(15))
        c.typed((320 - cw / 2, 180), s, font(15), GREEN, clamp((f - T_FIN + 1) / 12.0), "lm", cursor=False)
        for k, q in enumerate([(40, 60), (600, 70), (320, 190), (580, 200)]):
            if (f + k) % 3 == 0:
                c.sparkle(q)
    return c.image()


if __name__ == "__main__":
    main(render, N, "fewer_devs", [10, 30, 56, 84, 136])
