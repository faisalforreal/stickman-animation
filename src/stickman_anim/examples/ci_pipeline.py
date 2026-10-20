"""Explainer: how a CI/CD pipeline works. Parallel job groups light up in order, with typed step captions.

Edit JOBS / COLS / STEPS to describe your own pipeline.
Run:  stickman demo ci_pipeline [gif|gif-hd|video-hd|video-4k] [bg-black|bg-white]
"""
try:
    from stickman_anim import *  # noqa: F401,F403
except ImportError:              # running inside the Claude skill, next to stickman_lib.py
    import os
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from stickman_lib import *  # noqa: F401,F403

N = 132
FL = 322
YC = 110
T_PIPE = 22          # pipeline appears (after the question intro)

JOBS = {
    "build":   (["Build"], "1m 3s", 34, 43),
    "unit":    (["Unit tests"], "47s", 46, 55),
    "quality": (["Code quality"], "57s", 46, 58),
    "deps":    (["Dependency audit"], "38s", 46, 52),
    "publish": (["Publish", "Docker images"], "3m 42s", 60, 71),
    "scan_api": (["Container scan (API)"], "2m 4s", 74, 85),
    "scan_web": (["Container scan (web)"], "1m 32s", 74, 81),
    "deploy":  (["Deploy to", "DigitalOcean"], "1m 36s", 88, 99),
    "report":  (["Pipeline", "report"], "3s", 102, 107),
}
COLS = [(["build"], 62), (["unit", "quality", "deps"], 112), (["publish"], 100),
        (["scan_api", "scan_web"], 138), (["deploy"], 86), (["report"], 66)]
GAP = 9
TOTAL = sum(w for _, w in COLS) + GAP * (len(COLS) - 1)
X0 = (640 - TOTAL) / 2
COLX, _x = [], X0
for _k, _w in COLS:
    COLX.append((_x, _w))
    _x += _w + GAP

STEPS = [  # start frame, caption, sub-caption
    (22, "A git push triggers the pipeline", "Every commit starts an automatic run"),
    (34, "Build compiles and packages the app", "Source code becomes a runnable build"),
    (46, "Three checks run in parallel", "Unit tests, code quality and a dependency audit"),
    (60, "Docker images get published", "The app is packaged into images and pushed to a registry"),
    (74, "Images are scanned for vulnerabilities", "The API and web containers are checked side by side"),
    (88, "Passing images deploy to DigitalOcean", "The new version goes live"),
    (102, "A pipeline report summarises the run", "Results reach the team in seconds"),
]
T_FINAL = 114
QUESTION = "How my CI/CD pipeline works?"


def jstate(k, f):
    _, _, s, e = JOBS[k]
    return "ok" if f >= e else ("run" if f >= s else "idle")


def col_done(i, f):
    return all(jstate(k, f) == "ok" for k in COLS[i][0])


def render(f):
    c = Frame(f)
    tiny, small, lab = font(9), font(10), font(11)
    cap, sub, qfont, tfont = font(16), font(11), font(24), font(16)

    c.floor(FL)

    # ------------------------------------------------ intro: the question
    if f < T_PIPE:
        full = QUESTION
        w = c.tw(full, qfont)
        c.typed((320 - w / 2, 150), full, qfont, WHITE, clamp((f + 1) / 14.0), "lm", cursor=True)
        c.text((34, 340), "Developer", tiny, GREY, "mm")
        c.human(34, FL)
        c.robot(590, FL, eye=CYAN)
        c.text((590, 340), "AI Agent", tiny, GREY, "mm")
        return c.image()

    # ------------------------------------------------ title (small, top)
    t = QUESTION
    c.text((320 - c.tw(t, tfont) / 2, 22), t, tfont, WHITE, "lm")

    # ------------------------------------------------ pipeline
    appear = clamp((f - T_PIPE + 1) / 6.0)       # fade-in by drawing progressively
    for i, (keys, w) in enumerate(COLS):
        if i / float(len(COLS)) > appear:
            break
        x0, _ = COLX[i]
        n = len(keys)
        h = (48 if len(JOBS[keys[0]][0]) == 2 else 38) if n == 1 else 36
        ys = [YC] if n == 1 else [YC + (q - (n - 1) / 2.0) * 42 for q in range(n)]
        if n > 1:
            sts = [jstate(k, f) for k in keys]
            gcol = GREEN if all(s == "ok" for s in sts) else (CYAN if "run" in sts else DIM)
            c.rect((x0 - 5, ys[0] - h / 2 - 6), (x0 + w + 5, ys[-1] + h / 2 + 6), gcol, 2.0, 0.8)
        for k, yc in zip(keys, ys):
            lines, dur, s, e = JOBS[k]
            st = jstate(k, f)
            col = {"idle": DIM, "run": CYAN, "ok": GREEN}[st]
            c.rect((x0, yc - h / 2), (x0 + w, yc + h / 2), col, 2.3, 0.8)
            ic = (x0 + 11, yc)
            if st == "run":
                c.spinner(ic, 4.5)
            elif st == "ok":
                c.circle(ic, 5.5, GREEN, 1.8)
                c.check(ic, 7, GREEN, 1.8)
            else:
                c.circle(ic, 4.5, DIM, 1.8)
            rows = len(lines) + (1 if st == "ok" else 0)
            y = yc - (rows - 1) * 5.5
            for ln in lines:
                c.text((x0 + 21, y), ln, small, GREY if st == "idle" else WHITE)
                y += 11
            if st == "ok":
                c.text((x0 + 21, y), dur, tiny, GREEN)
            if st == "run":
                p = clamp((f - s) / float(e - s))
                c.line((x0 + 5, yc + h / 2 - 4), (x0 + 5 + (w - 10) * p, yc + h / 2 - 4), CYAN, 2, 0.3)
        if i < len(COLS) - 1:
            a = (x0 + w + (5 if n > 1 else 0), YC)
            b = (COLX[i + 1][0] - (5 if len(COLS[i + 1][0]) > 1 else 0), YC)
            lcol = GREEN if col_done(i, f) else DIM
            c.line(a, b, lcol, 2, 0.4)
            c.circle(a, 2.6, lcol, fill=True)
            c.circle(b, 2.6, lcol, fill=True)

    # ------------------------------------------------ caption (explains the active step)
    finale = f >= T_FINAL
    if finale:
        s0, ctext, stext, stepno = T_FINAL, "All green: from push to production, automatically", \
            "The same flow runs on every single commit", None
        ccol = GREEN
    else:
        idx = max(i for i in range(len(STEPS)) if STEPS[i][0] <= f)
        s0, ctext, stext = STEPS[idx]
        stepno = idx + 1
        ccol = WHITE
    prog = clamp((f - s0 + 1) / 8.0)
    if stepno:
        c.text((320, 196), "STEP %d / 7" % stepno, small, CYAN, "mm")
    cw = c.tw(ctext, cap)
    c.typed((320 - cw / 2, 220), ctext, cap, ccol, prog, "lm", cursor=False)
    sw = c.tw(stext, sub)
    if prog >= 1:
        c.text((320 - sw / 2, 244), stext, sub, GREY, "lm")

    # ------------------------------------------------ developer (left)
    push_start = STEPS[0][0]
    c.human(34, FL, hr=(66, 280 - (c.wig if push_start <= f < push_start + 8 else 0)),
            thumbs_up=finale and False)
    c.rect((62, 262), (72, 282), CYAN if f < push_start + 8 else WHITE, 2, 0.4)
    if f >= push_start:
        c.rect((82, 270), (152, 294), CYAN if f < push_start + 8 else WHITE, 2.2, 0.7)
        c.typed((90, 282), "git push", lab, WHITE, clamp((f - push_start + 1) / 6.0), "lm", cursor=False)
    c.text((34, 340), "Developer", tiny, GREY, "mm")
    if 28 <= f < 34:
        tt = (f - 27) / 6.0
        bx = COLX[0][0] + COLS[0][1] / 2
        c.packet(arc_lerp((118, 268), (bx, YC + 30), tt, 18), CYAN)

    # ------------------------------------------------ agent (right): receives report
    rx = 590
    done_all = f >= JOBS["report"][3]
    c.robot(rx, FL, eye=GREEN if done_all else CYAN, cheer=f >= T_FINAL + 4)
    c.text((rx, 340), "AI Agent", tiny, GREY, "mm")
    if JOBS["report"][3] <= f < JOBS["report"][3] + 7:
        tt = (f - JOBS["report"][3] + 1) / 7.0
        bx = COLX[-1][0] + COLS[-1][1] / 2
        c.packet(arc_lerp((bx, YC + 30), (rx - 20, 248), tt, 14), GREEN)
    if f >= T_FINAL:
        for k, p in enumerate([(300, 280), (160, 190), (500, 190), (610, 250)]):
            if (f + k) % 3 == 0:
                c.sparkle(p)

    return c.image()


if __name__ == "__main__":
    main(render, N, "ci_pipeline", [10, 26, 38, 50, 64, 78, 92, 126])
