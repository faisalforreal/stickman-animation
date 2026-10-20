"""stickman_anim - a tiny toolkit for hand-drawn, stop-motion style stickman animations.

Everything is drawn with Pillow on a 640x360 logical canvas, supersampled and downsampled, so lines stay
crisp at any output size. Every primitive is re-jittered per frame (seeded by the frame number), which is
what makes the animation read as stop-motion.

Minimal script::

    from stickman_anim import *            # inside the Claude skill: from stickman_lib import *

    N = 40

    def render(f):
        c = Frame(f)                       # fresh canvas, jitter seeded by the frame number
        c.floor(322)
        c.robot(120, 322, eye=CYAN, hr=(180, 258))
        c.text((320, 40), "Hello", font(20), WHITE, "mm")
        return c.image()

    if __name__ == "__main__":             # the guard lets multiprocessing workers import this file
        main(render, N, "hello")           # honours the format / theme flags, writes hello.gif or hello.mp4

Run it with flags: ``python hello.py video-4k bg-white`` (see FORMATS and parse_flags below).
"""
__version__ = "0.2.0"

import glob
import math
import random

from PIL import Image, ImageDraw, ImageFont

# ------------------------------------------------------------------ flags
# Output format and colour theme are chosen with FLAGS, read at import time from the script's command line
# (e.g. `python make_x.py video-4k bg-white`) or from the STICKMAN_FLAGS env var. They must be known before
# the classes below are defined, which is why this runs first. Unknown words are ignored; a leading "--" is fine.
#   format : gif | gif-hd | video-hd | video-4k            (default gif-hd)
#   theme  : bg-black (= fg-white, default) | bg-white (= fg-black)
import os as _os
import sys as _sys

FORMATS = {                     # flag -> (kind, quality preset, description)
    "gif": ("gif", "sd", "GIF 640x360"),
    "gif-hd": ("gif", "hd", "GIF 1280x720"),
    "video-hd": ("mp4", "fhd", "MP4 1920x1080"),
    "video-4k": ("mp4", "4k", "MP4 3840x2160"),
}


def parse_flags(words):
    """Return (format_flag, theme) from a list of words. theme is 'dark' (bg-black/fg-white) or 'light'."""
    words = [w.lstrip("-").lower() for w in words]
    fmt = next((w for w in words if w in FORMATS), "gif-hd")
    bg = "white" if "bg-white" in words else ("black" if "bg-black" in words else None)
    fg = "black" if "fg-black" in words else ("white" if "fg-white" in words else None)
    if bg is None and fg is not None:
        bg = "white" if fg == "black" else "black"        # only the ink was named: pick the matching ground
    if bg is not None and fg is not None and bg == fg:
        raise SystemExit("stickman flags: bg-%s with fg-%s would be invisible. Use bg-black+fg-white or bg-white+fg-black." % (bg, fg))
    return fmt, ("light" if bg == "white" else "dark")


_ALL_FLAGS = set(FORMATS) | {"bg-black", "bg-white", "fg-black", "fg-white"}
FORMAT, THEME = parse_flags(_sys.argv[1:] + _os.environ.get("STICKMAN_FLAGS", "").split())

# ------------------------------------------------------------------ palette
# WHITE means "the ink colour" (white on a dark ground, near-black on a light one); BG is the ground.
if THEME == "dark":                       # bg-black, fg-white
    WHITE = (245, 245, 245)
    GREY = (125, 125, 125)
    DIM = (65, 65, 65)                    # idle / inactive outlines
    CYAN = (80, 220, 255)                 # active / working
    GREEN = (90, 255, 140)                # done / success
    RED = (255, 95, 95)                   # failure (use sparingly)
    BG = (0, 0, 0)
else:                                     # bg-white, fg-black (accents darkened so they stay readable)
    WHITE = (18, 18, 18)
    GREY = (115, 115, 115)
    DIM = (196, 196, 196)
    CYAN = (0, 140, 200)
    GREEN = (0, 150, 70)
    RED = (215, 45, 45)
    BG = (255, 255, 255)
INK = WHITE

W, H = 640, 360            # logical canvas (all coordinates are in these units)
S = 4                      # supersample factor (set by set_quality; drawing happens at S x logical)
OUT = (1280, 720)          # pixel size of the finished frames (set by set_quality)

# name -> (output width, supersample). Supersample = 2x the output scale, so every edge is anti-aliased.
QUALITY = {"sd": (640, 2), "hd": (1280, 4), "fhd": (1920, 6), "4k": (3840, 12)}


def set_quality(name="hd"):
    """Pick the output resolution: 'sd' 640x360, 'hd' 1280x720 (default), 'fhd' 1920x1080, '4k' 3840x2160.
    Call it once at the top of a script, BEFORE creating any Frame. Coordinates never change: the same
    640x360 layout is simply drawn with more pixels, so lines and text stay sharp."""
    global S, OUT
    ow, ss = QUALITY[name] if isinstance(name, str) else name
    S, OUT = ss, (ow, ow * 9 // 16)
    _FONT_CACHE.clear()
    return OUT


# ------------------------------------------------------------------ helpers
def lerp(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def arc_lerp(a, b, t, height=14):
    """Point on a lifted arc from a to b - good for packets / cards 'thrown' between things."""
    p = lerp(a, b, t)
    return (p[0], p[1] - height * math.sin(math.pi * t))


def along(points, t):
    """Point at fraction t (0..1) along a polyline."""
    segs = [(points[i], points[i + 1]) for i in range(len(points) - 1)]
    lens = [math.dist(a, b) for a, b in segs]
    target = t * sum(lens)
    for (a, b), l in zip(segs, lens):
        if target <= l or (a, b) == segs[-1]:
            return lerp(a, b, min(1, target / l if l else 1))
        target -= l
    return points[-1]


_FONT_DIRS = [
    "/usr/share/fonts", "/usr/local/share/fonts", _os.path.expanduser("~/.fonts"),
    _os.path.expanduser("~/.local/share/fonts"),                      # Linux
    "/System/Library/Fonts", "/System/Library/Fonts/Supplemental", "/Library/Fonts",
    _os.path.expanduser("~/Library/Fonts"),                           # macOS
    _os.path.join(_os.environ.get("WINDIR", "C:\\Windows"), "Fonts"),   # Windows
]
_LATIN_BOLD = ["LiberationSans-Bold.ttf", "DejaVuSans-Bold.ttf", "Arial Bold.ttf", "arialbd.ttf", "Helvetica.ttc"]
_LATIN_REG = ["LiberationSans-Regular.ttf", "DejaVuSans.ttf", "Arial.ttf", "arial.ttf", "Helvetica.ttc"]
# Bangla needs a font with Bengali glyphs AND complex-text shaping (libraqm) so conjuncts join correctly.
_BANGLA = ["FreeSans.ttf", "NotoSansBengali-Regular.ttf", "NotoSansBengali[wdth,wght].ttf",
           "Kohinoor Bangla.ttc", "Bangla Sangam MN.ttc", "Nirmala.ttf", "vrinda.ttf", "Lohit-Bengali.ttf"]


def _search(names):
    for d in _FONT_DIRS:
        if not _os.path.isdir(d):
            continue
        for n in names:
            hits = glob.glob(_os.path.join(glob.escape(d), "**", glob.escape(n)), recursive=True)
            if hits:
                return hits[0]
    return None


def find_font(bold=True, bangla=False):
    """Locate a usable font file. Override with the STICKMAN_FONT / STICKMAN_FONT_BANGLA env vars.
    Falls back to Pillow's built-in font (works, but looks plain) when nothing is found."""
    env = _os.environ.get("STICKMAN_FONT_BANGLA" if bangla else "STICKMAN_FONT")
    if env and _os.path.isfile(env):
        return env
    if bangla:
        return _search(_BANGLA)
    return _search(_LATIN_BOLD if bold else _LATIN_REG)


_FONT_CACHE = {}
set_quality(FORMATS[FORMAT][1])   # from the format flag (default gif-hd -> 1280x720). Can still be overridden in code.


def font(size, bangla=False):
    key = (size, bangla)
    if key not in _FONT_CACHE:
        p = find_font(bangla=bangla)
        _FONT_CACHE[key] = ImageFont.truetype(p, size * S) if p else ImageFont.load_default(size * S)
    return _FONT_CACHE[key]


# ------------------------------------------------------------------ canvas
class Frame:
    def __init__(self, f, width=W, height=H):
        self.f = f
        self.w, self.h = width, height
        self.rng = random.Random(f * 7919 + 13)
        self.img = Image.new("RGB", (width * S, height * S), BG)
        self.d = ImageDraw.Draw(self.img)
        self.wig = 3 if f % 2 else 0          # tiny alternating offset for typing hands

    # ---- low-level jittered primitives
    def j(self, p, a=1.2):
        return (p[0] + self.rng.uniform(-a, a), p[1] + self.rng.uniform(-a, a))

    def P(self, p):
        return (p[0] * S, p[1] * S)

    def line(self, a, b, col=WHITE, w=2.6, jit=1.2):
        a, b = self.j(a, jit), self.j(b, jit)
        self.d.line([self.P(a), self.P(b)], fill=col, width=int(w * S))
        r = w * S / 2                          # round caps
        for q in (self.P(a), self.P(b)):
            self.d.ellipse([q[0] - r, q[1] - r, q[0] + r, q[1] + r], fill=col)

    def poly(self, pts, col=WHITE, w=2.6, close=True, jit=1.2):
        n = len(pts)
        for i in range(n if close else n - 1):
            self.line(pts[i], pts[(i + 1) % n], col, w, jit)

    def rect(self, a, b, col=WHITE, w=2.6, jit=1.2):
        self.poly([a, (b[0], a[1]), b, (a[0], b[1])], col, w, True, jit)

    def circle(self, c, r, col=WHITE, w=2.6, fill=False):
        c = self.j(c, 0.9)
        rr = r + self.rng.uniform(-0.7, 0.7)
        box = [(c[0] - rr) * S, (c[1] - rr) * S, (c[0] + rr) * S, (c[1] + rr) * S]
        if fill:
            self.d.ellipse(box, fill=col)
        else:
            self.d.ellipse(box, outline=col, width=int(w * S))

    def dashed(self, a, b, col=DIM, seg=8):
        n = max(2, int(math.dist(a, b) // seg))
        for q in range(0, n, 2):
            self.line(lerp(a, b, q / n), lerp(a, b, min(1, (q + 1) / n)), col, 1.6, 0.3)

    # ---- text (jittered; pass a font from font())
    def text(self, xy, s, fnt, col=WHITE, anchor="lm"):
        self.d.text((xy[0] * S + self.rng.uniform(-0.6 * S, 0.6 * S), xy[1] * S + self.rng.uniform(-0.6 * S, 0.6 * S)),
                    s, font=fnt, fill=col, anchor=anchor)

    def tw(self, s, fnt):
        return self.d.textlength(s, font=fnt) / S

    def typed(self, xy, s, fnt, col, progress, anchor="lm", cursor=True):
        """Typewriter reveal by characters (ASCII). progress 0..1. For Bangla/complex scripts use wipe()."""
        n = len(s) if progress >= 1 else int(progress * len(s))
        shown = s[:n]
        self.text(xy, shown, fnt, col, anchor)
        if cursor and progress < 1 and self.f % 2 == 0:
            x = xy[0] + self.tw(shown, fnt) + 3 if anchor == "lm" else xy[0]
            self.line((x, xy[1] - 9), (x, xy[1] + 9), CYAN, 2, 0.3)

    def wipe(self, xy, s, fnt, col, progress, height=70):
        """Left-to-right reveal of a fully shaped line (safe for Bangla, Arabic, etc.). xy = left/top."""
        tw = self.d.textlength(s, font=fnt)
        layer = Image.new("RGBA", (int(tw) + 40, height * S), (0, 0, 0, 0))
        ImageDraw.Draw(layer).text((10, 0), s, font=fnt, fill=col)
        cut = int(10 + (tw + 6) * clamp(progress))
        layer = layer.crop((0, 0, min(cut, layer.width), layer.height))
        self.img.paste(layer, (int(xy[0] * S) - 10, int(xy[1] * S)), layer)

    # ---- icons
    def spinner(self, c, r, col=CYAN):
        c = self.j(c, 0.6)
        a0 = (self.f * 40) % 360
        box = [(c[0] - r) * S, (c[1] - r) * S, (c[0] + r) * S, (c[1] + r) * S]
        self.d.arc(box, a0, a0 + 250, fill=col, width=int(2.6 * S))

    def check(self, c, s=10, col=GREEN, w=3.0):
        self.poly([(c[0] - 0.5 * s, c[1]), (c[0] - 0.1 * s, c[1] + 0.4 * s), (c[0] + 0.55 * s, c[1] - 0.4 * s)],
                  col, w, False, 0.5)

    def cross(self, c, s=10, col=RED, w=3.0):
        self.line((c[0] - s * .45, c[1] - s * .45), (c[0] + s * .45, c[1] + s * .45), col, w, 0.5)
        self.line((c[0] + s * .45, c[1] - s * .45), (c[0] - s * .45, c[1] + s * .45), col, w, 0.5)

    def sparkle(self, c, s=6, col=GREEN):
        self.line((c[0] - s, c[1]), (c[0] + s, c[1]), col, 2, 0.3)
        self.line((c[0], c[1] - s), (c[0], c[1] + s), col, 2, 0.3)

    def packet(self, p, col=WHITE):
        """Little envelope - a message / ticket in flight."""
        self.rect((p[0] - 9, p[1] - 6), (p[0] + 9, p[1] + 6), col, 2.2, 0.5)
        self.line((p[0] - 9, p[1] - 6), (p[0], p[1] + 1), col, 1.6, 0.3)
        self.line((p[0] + 9, p[1] - 6), (p[0], p[1] + 1), col, 1.6, 0.3)

    def floor(self, y, x0=14, x1=626):
        self.line((x0, y), (x1, y), DIM, 2, 0.8)

    # ---- characters
    def arm(self, shoulder, hand, col=WHITE):
        """Two-segment arm with a slightly dropped elbow. Hands up to ~70px from the shoulder look natural."""
        mid = lerp(shoulder, hand, 0.5)
        el = (mid[0], mid[1] + 10)
        self.line(shoulder, el, col)
        self.line(el, hand, col)

    def robot(self, cx, fl, eye=CYAN, hl=None, hr=None, cheer=False, head_bob=True):
        """Robot-stickman AGENT: square head, two eyes, mouth grille, antenna. fl = floor y.
        hl/hr = absolute hand targets (None = arm hangs idle). cheer = both arms up, waving."""
        f = self.f
        bob = 1 if (head_bob and f % 2) else 0
        hy = fl - 86 + bob
        e = DIM if f % 14 == 0 else eye          # periodic blink
        self.rect((cx - 11, hy - 10), (cx + 11, hy + 10), WHITE, 2.6, 1.0)
        self.circle((cx - 4, hy - 2), 2.5, e, fill=True)
        self.circle((cx + 5, hy - 2), 2.5, e, fill=True)
        self.line((cx - 5, hy + 5), (cx + 6, hy + 5), WHITE, 1.8, 0.4)
        self.line((cx, hy - 10), (cx, hy - 17), WHITE, 2, 0.4)
        self.circle((cx, hy - 19), 2.2, e, fill=True)
        self.line((cx, hy + 10), (cx, fl - 40), WHITE, 2.6, 0.6)
        self.line((cx, fl - 40), (cx - 11, fl), WHITE, 2.6, 0.6)
        self.line((cx, fl - 40), (cx + 11, fl), WHITE, 2.6, 0.6)
        self.line((cx - 11, fl), (cx - 19, fl), WHITE, 2.6, 0.4)
        self.line((cx + 11, fl), (cx + 19, fl), WHITE, 2.6, 0.4)
        sh = (cx, fl - 66)
        self.circle(sh, 2.2, WHITE, fill=True)
        if cheer:
            up = 5 * (f % 2)
            self.arm(sh, (cx - 18, fl - 108 - up))
            self.arm(sh, (cx + 18, fl - 108 - (5 - up)))
            return
        for hand, sx in ((hl, -1), (hr, 1)):
            if hand:
                self.arm(sh, hand)
            else:
                self.line(sh, (cx + sx * 9, fl - 50))
                self.line((cx + sx * 9, fl - 50), (cx + sx * 10, fl - 36))

    def human(self, cx, fl, hl=None, hr=None, thumbs_up=False, glasses=True, smile=False):
        """HUMAN stickman: round head (+ glasses so it reads as 'the person'). Same hand API as robot."""
        f = self.f
        hy = fl - 92
        self.circle((cx, hy), 10, WHITE, 2.6)
        if glasses:
            self.circle((cx - 4, hy - 1), 3.6, WHITE, 1.6)
            self.circle((cx - 4, hy - 1), 1.2, WHITE, fill=True)
        if smile:
            self.poly([(cx - 6, hy + 5), (cx - 3, hy + 8), (cx + 1, hy + 5)], GREEN, 1.8, False, 0.3)
        self.line((cx, hy + 10), (cx, fl - 44))
        self.line((cx, fl - 44), (cx - 8, fl))
        self.line((cx, fl - 44), (cx + 8, fl))
        sh = (cx, fl - 72)
        self.circle(sh, 2, WHITE, fill=True)
        if thumbs_up:
            hand = (cx - 20, fl - 100 - (2 if f % 2 else 0))
            self.arm(sh, hand)
            self.line(hand, (hand[0], hand[1] - 8), WHITE, 2.4, 0.3)
        elif hl:
            self.arm(sh, hl)
        else:
            self.line(sh, (cx - 7, fl - 58))
            self.line((cx - 7, fl - 58), (cx - 9, fl - 46))
        if hr:
            self.arm(sh, hr)
        else:
            self.line(sh, (cx + 7, fl - 58))
            self.line((cx + 7, fl - 58), (cx + 9, fl - 46))

    # ---- UI furniture
    def window(self, a, b, title, title_font=None):
        """Generic chat/app window: frame, title bar, three dots. NEVER draw real brand logos - label with text."""
        self.rect(a, b, WHITE, 2.4, 1.0)
        self.line((a[0], a[1] + 22), (b[0], a[1] + 22), WHITE, 2, 0.6)
        self.text((a[0] + 9, a[1] + 11), title, title_font or font(11), WHITE)
        for q in range(3):
            self.circle((b[0] - 30 + q * 10, a[1] + 11), 2.2, GREY, fill=True)

    def node(self, center, w, h, label, state="idle", label_font=None):
        """Pipeline / stage box. state: idle (dim) | run (cyan, spinner) | ok (green, check) | fail (red, cross)."""
        col = {"idle": DIM, "run": CYAN, "ok": GREEN, "fail": RED}[state]
        self.rect((center[0] - w / 2, center[1] - h / 2), (center[0] + w / 2, center[1] + h / 2), col, 2.4, 0.9)
        self.text((center[0], center[1] - 5), label, label_font or font(11),
                  GREY if state == "idle" else WHITE, "mm")
        c = (center[0], center[1] + 8)
        if state == "run":
            self.spinner(c, 5)
        elif state == "ok":
            self.check(c, 9, GREEN, 2.4)
        elif state == "fail":
            self.cross(c, 10, RED, 2.4)

    def avatar(self, image, center, radius, ring=WHITE):
        """Paste a user-supplied picture into a round badge (white-backed art survives the black canvas)."""
        side = radius * 2 * S
        im = image.resize((side, side), Image.LANCZOS)
        mask = Image.new("L", im.size, 0)
        ImageDraw.Draw(mask).ellipse([0, 0, side - 1, side - 1], fill=255)
        jx, jy = self.rng.uniform(-1.2, 1.2), self.rng.uniform(-1.2, 1.2)
        self.img.paste(im, (int((center[0] - radius + jx) * S), int((center[1] - radius + jy) * S)), mask)
        self.circle(center, radius, ring, 2.4)

    def image(self, size=None):
        """Downsample the supersampled canvas to the size chosen with set_quality() (default 1280x720).
        Pass size=(w, h) only for a one-off custom size."""
        return self.img.resize(size or OUT, Image.LANCZOS)


def load_avatar(path):
    """Open a user image, flatten transparency onto white, crop to a centered square."""
    raw = Image.open(path).convert("RGBA")
    flat = Image.new("RGBA", raw.size, (255, 255, 255, 255))
    flat.alpha_composite(raw)
    flat = flat.convert("RGB")
    s = min(flat.size)
    x0 = (flat.width - s) // 2
    return flat.crop((x0, 0, x0 + s, s))


# ------------------------------------------------------------------ output
def save_gif(frames, path, ms=120, colors=64):
    """Save a looping GIF. Frames are quantised to a small palette without dithering: the art is
    white/grey/cyan/green on black, so 64 colours keep the anti-aliased edges and keep HD files small."""
    q = [im.quantize(colors=colors, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE) for im in frames]
    q[0].save(path, save_all=True, append_images=q[1:], duration=ms, loop=0, optimize=True, disposal=1)


_RENDER = None          # set before forking so worker processes inherit the render function


def _render_one(f):
    im = _RENDER(f).convert("RGB")
    return im.size, im.tobytes()


def _resolve_workers(workers):
    if workers in (None, "auto"):
        import multiprocessing as mp
        if "fork" not in mp.get_all_start_methods():
            return 1                                  # Windows / macOS spawn: stay single-process
        return max(1, min(_os.cpu_count() or 1, 4))
    return max(1, int(workers))


def iter_frames(render, n, workers="auto"):
    """Yield render(0) .. render(n-1) in order, using up to `workers` processes (fork platforms only).
    Frames depend only on their number, so the result is identical for any worker count."""
    workers = _resolve_workers(workers)
    if workers <= 1 or n < 4:
        for f in range(n):
            yield render(f)
        return
    import multiprocessing as mp
    global _RENDER
    _RENDER = render
    with mp.get_context("fork").Pool(workers) as pool:
        for size, raw in pool.imap(_render_one, range(n), chunksize=2):
            yield Image.frombytes("RGB", size, raw)


def render_mp4(render, n, path, ms=120, crf=14, loops=3, workers="auto"):
    """Render frames one at a time straight into ffmpeg (H.264), so memory stays flat even at 4K
    (140 frames of 3840x2160 would be ~3.5 GB if kept in a list). `render(f)` returns a PIL image.
    The finished clip is repeated `loops` times (stream copy, no re-encode). Needs ffmpeg.
    Raw RGB goes to ffmpeg, which is robust at any size, unlike piping PNGs at 4K."""
    import shutil
    import subprocess
    import tempfile
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg is required for MP4 output (install it, or use a gif / gif-hd format flag)")
    frames = iter_frames(render, n, workers)
    first = next(frames)
    w, h = first.size
    w2, h2 = w - w % 2, h - h % 2
    tmp = tempfile.mktemp(suffix=".mp4") if loops > 1 else path
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "%dx%d" % (w, h),
           "-framerate", str(round(1000.0 / ms, 3)), "-i", "-",
           "-vf", "crop=%d:%d:0:0,fps=30" % (w2, h2), "-c:v", "libx264", "-preset", "slow",
           "-crf", str(crf), "-pix_fmt", "yuv420p", "-movflags", "+faststart", tmp]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    p.stdin.write(first.convert("RGB").tobytes())
    for im in frames:
        p.stdin.write(im.convert("RGB").tobytes())
    p.stdin.close()
    if p.wait() != 0:
        raise RuntimeError("ffmpeg failed while encoding " + path)
    if loops > 1:
        subprocess.check_call(["ffmpeg", "-y", "-loglevel", "error", "-stream_loop", str(loops - 1), "-i", tmp,
                               "-c", "copy", "-movflags", "+faststart", path])
        _os.remove(tmp)


def save_mp4(frames, path, ms=120, crf=14, loops=3):
    """Same as render_mp4 for frames already in a list (fine up to FHD; use render_mp4 for 4K)."""
    render_mp4(lambda f: frames[f], len(frames), path, ms, crf, loops)


def contact_sheet(frames, idxs, path, cols=2, thumb_w=640):
    """Tile chosen frames into one PNG so you can eyeball the animation in a single look.
    Thumbnails are scaled to thumb_w so an HD/4K render does not make a gigantic sheet."""
    ims = []
    for i in idxs:
        im = frames[i]
        if im.width != thumb_w:
            im = im.resize((thumb_w, im.height * thumb_w // im.width), Image.LANCZOS)
        ims.append(im)
    w, h = ims[0].size
    rows = (len(ims) + cols - 1) // cols
    sheet = Image.new("RGB", (w * cols, h * rows))
    for k, im in enumerate(ims):
        sheet.paste(im, ((k % cols) * w, (k // cols) * h))
    sheet.save(path)


# ------------------------------------------------------------------ one-call export (honours the format flag)
def export(render, n, base, ms=120, loops=3, workers="auto"):
    """Render `n` frames with `render(f)` and write them in the format chosen by the flag:
    gif / gif-hd -> <base>.gif, video-hd / video-4k -> <base>.mp4 (streamed, looped `loops` times).
    `workers` = number of processes ("auto" = up to 4 on fork platforms). Returns the path written."""
    kind = FORMATS[FORMAT][0]
    if kind == "gif":
        path = base + ".gif"
        save_gif(list(iter_frames(render, n, workers)), path, ms)
    else:
        path = base + ".mp4"
        render_mp4(render, n, path, ms, loops=loops, workers=workers)
    return path


def sheet(render, idxs, path, cols=2):
    """Render only the chosen frames and tile them into a small contact sheet for a visual check."""
    frames = [render(i) for i in idxs]
    contact_sheet(frames, list(range(len(frames))), path, cols)


def describe():
    return "%s, %s theme (%s)" % (FORMATS[FORMAT][2], "bg-black/fg-white" if THEME == "dark" else "bg-white/fg-black", FORMAT)


def main(render, n, name, sheet_frames=None, ms=120):
    """Standard script ending: `main(render, N, "name", [frames to eyeball])`.
    The output base name is the first command-line word that is not a flag (default `name`)."""
    words = [w for w in _sys.argv[1:] if w.lstrip("-").lower() not in _ALL_FLAGS and not w.startswith("-")]
    base = words[0] if words else name
    print("rendering:", describe())
    if sheet_frames:
        sheet(render, sheet_frames, base + "_sheet.png")
    print("wrote", export(render, n, base, ms))
