"""Motion, Easing, Particles, Virtual Camera, and Transitions for stickman_anim.

Provides:
- Comprehensive easing curves: linear, quad, cubic, back (overshoot), elastic, bounce, and damped spring.
- Sequenced stagger reveals and squash-and-stretch helpers.
- Keyframe tracks (`Track`) for smooth scalar and 2D point interpolation.
- Deterministic stop-motion particle emitters: confetti, sparks, smoke puffs, and rain.
- Action speed lines and radial focus lines.
- Virtual 2D camera with pan, zoom, shake, smooth follow, and multi-plane parallax.
- Pure-Pillow artistic scene transitions: wipe, iris, ink splash blot, and zoom.
"""

import math
import random
from typing import List, Tuple, Optional, Callable, Dict, Any, Union
from PIL import Image, ImageDraw
from .paths import Point, dist, lerp_pt

# ------------------------------------------------------------------ 1. Easing Curves
# Each function takes t in [0.0, 1.0] and returns an eased value.


def ease_linear(t: float) -> float:
    return max(0.0, min(1.0, t))


def ease_in_quad(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t


def ease_out_quad(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * (2.0 - t)


def ease_in_out_quad(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 2.0 * t * t if t < 0.5 else -1.0 + (4.0 - 2.0 * t) * t


def ease_in_cubic(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * t


def ease_out_cubic(t: float) -> float:
    t = max(0.0, min(1.0, t)) - 1.0
    return t * t * t + 1.0


def ease_in_out_cubic(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 4.0 * t * t * t if t < 0.5 else (t - 1.0) * (2.0 * t - 2.0) * (2.0 * t - 2.0) + 1.0


def ease_out_back(t: float, overshoot: float = 1.70158) -> float:
    """Over-shoots target slightly then snaps back. Classic snappy UI / comic pop."""
    t = max(0.0, min(1.0, t)) - 1.0
    return t * t * ((overshoot + 1.0) * t + overshoot) + 1.0


def ease_in_back(t: float, overshoot: float = 1.70158) -> float:
    """Anticipation wind-up before launching forward."""
    t = max(0.0, min(1.0, t))
    return t * t * ((overshoot + 1.0) * t - overshoot)


def ease_in_out_back(t: float, overshoot: float = 1.70158) -> float:
    t = max(0.0, min(1.0, t)) * 2.0
    s = overshoot * 1.525
    if t < 1.0:
        return 0.5 * (t * t * ((s + 1.0) * t - s))
    t -= 2.0
    return 0.5 * (t * t * ((s + 1.0) * t + s) + 2.0)


def ease_out_elastic(t: float, bounciness: float = 0.3) -> float:
    """Organic jelly elastic wobble."""
    t = max(0.0, min(1.0, t))
    if t == 0.0 or t == 1.0:
        return t
    p = bounciness
    s = p / 4.0
    return math.pow(2.0, -10.0 * t) * math.sin((t - s) * (2.0 * math.pi) / p) + 1.0


def ease_out_bounce(t: float) -> float:
    """Gravity ball bouncing until settled."""
    t = max(0.0, min(1.0, t))
    if t < (1.0 / 2.75):
        return 7.5625 * t * t
    elif t < (2.0 / 2.75):
        t -= 1.5 / 2.75
        return 7.5625 * t * t + 0.75
    elif t < (2.5 / 2.75):
        t -= 2.25 / 2.75
        return 7.5625 * t * t + 0.9375
    else:
        t -= 2.625 / 2.75
        return 7.5625 * t * t + 0.984375


def spring(t: float, mass: float = 1.0, stiffness: float = 100.0, damping: float = 10.0) -> float:
    """Simulate a physical damped harmonic oscillator settling from 0 to 1."""
    if t <= 0.0:
        return 0.0
    omega0 = math.sqrt(stiffness / mass)
    zeta = damping / (2.0 * math.sqrt(stiffness * mass))

    if zeta < 1.0:
        # Underdamped oscillation
        omega_d = omega0 * math.sqrt(1.0 - zeta * zeta)
        decay = math.exp(-zeta * omega0 * t)
        val = 1.0 - decay * (math.cos(omega_d * t) + (zeta * omega0 / omega_d) * math.sin(omega_d * t))
        return val
    else:
        # Critically damped or overdamped
        decay = math.exp(-omega0 * t)
        return 1.0 - decay * (1.0 + omega0 * t)


def stagger(index: int, total_items: int, progress: float, overlap: float = 0.5) -> float:
    """
    Calculate 0.0..1.0 staggered progress for the i-th item in a sequence.
    overlap in (0..1): 0 = strictly one after another; 0.8 = high cascade overlap.
    """
    if total_items <= 1:
        return progress
    span = (1.0 - overlap) / max(1, total_items - 1)
    start_t = index * span
    duration = span + overlap
    p = (progress - start_t) / max(1e-4, duration)
    return max(0.0, min(1.0, p))


def squash_stretch(t: float, intensity: float = 0.3) -> Tuple[float, float]:
    """
    Returns (scale_x, scale_y) for cartoon squash and stretch during impacts or jumps.
    Volume is preserved (sx * sy ≈ 1.0).
    """
    val = math.sin(t * math.pi) * intensity
    sx = 1.0 + val
    sy = 1.0 / max(0.1, sx)
    return (sx, sy)


EASING_MAP: Dict[str, Callable[[float], float]] = {
    "linear": ease_linear,
    "in_quad": ease_in_quad,
    "out_quad": ease_out_quad,
    "in_out_quad": ease_in_out_quad,
    "in_cubic": ease_in_cubic,
    "out_cubic": ease_out_cubic,
    "in_out_cubic": ease_in_out_cubic,
    "out_back": ease_out_back,
    "in_back": ease_in_back,
    "in_out_back": ease_in_out_back,
    "elastic": ease_out_elastic,
    "bounce": ease_out_bounce,
}


# ------------------------------------------------------------------ 2. Keyframe Tracks
class Track:
    """
    Multi-keyframe animator for scalars or 2D points.
    Keyframes: list of (time, value), sorted by time.
    """
    def __init__(self, keyframes: Optional[List[Tuple[float, Any]]] = None, easing: str = "out_cubic"):
        self.keyframes: List[Tuple[float, Any]] = sorted(keyframes or [], key=lambda k: k[0])
        self.default_easing = easing

    def add(self, t: float, val: Any) -> "Track":
        self.keyframes.append((t, val))
        self.keyframes.sort(key=lambda k: k[0])
        return self

    def at(self, t: float, easing: Optional[str] = None) -> Any:
        if not self.keyframes:
            return 0.0
        if t <= self.keyframes[0][0]:
            return self.keyframes[0][1]
        if t >= self.keyframes[-1][0]:
            return self.keyframes[-1][1]

        # Find enclosing interval
        ease_fn = EASING_MAP.get(easing or self.default_easing, ease_out_cubic)
        for i in range(len(self.keyframes) - 1):
            t0, v0 = self.keyframes[i]
            t1, v1 = self.keyframes[i + 1]
            if t0 <= t <= t1:
                dt = max(1e-4, t1 - t0)
                frac = ease_fn((t - t0) / dt)
                if isinstance(v0, (tuple, list)) and len(v0) == 2:
                    return lerp_pt(v0, v1, frac)
                else:
                    return v0 + (v1 - v0) * frac
        return self.keyframes[-1][1]


# ------------------------------------------------------------------ 3. Particles & Speed Lines
class ParticleSystem:
    """Deterministic, stop-motion stylized particles."""

    @staticmethod
    def confetti(frame_obj: Any, origin: Point, t: float, count: int = 24, seed: int = 42) -> None:
        """Fluttering colorful rectangles that fall with gravity and sway."""
        c = frame_obj
        colors = [(255, 95, 95), (80, 220, 255), (90, 255, 140), (255, 230, 0), (200, 140, 255)]
        rng = random.Random(seed)

        for i in range(count):
            vx = rng.uniform(-40.0, 40.0)
            vy = rng.uniform(-60.0, -10.0)
            sway_f = rng.uniform(2.0, 6.0)
            col = colors[i % len(colors)]

            # Particle motion over time t
            px = origin[0] + vx * t + math.sin(t * sway_f + i) * 12.0
            py = origin[1] + vy * t + 45.0 * t * t  # gravity
            rot = t * 8.0 + i

            # Draw small fluttering quad
            pw, ph = 4.0, 6.0
            pts = [
                (px - pw, py - ph),
                (px + pw, py - ph),
                (px + pw, py + ph),
                (px - pw, py + ph)
            ]
            c.poly(pts, col=col, w=1.8, close=True)

    @staticmethod
    def sparks(frame_obj: Any, origin: Point, t: float, count: int = 16, seed: int = 42, col: Tuple[int, int, int] = (255, 230, 0)) -> None:
        """Bright radiating spark lines with velocity decay."""
        c = frame_obj
        rng = random.Random(seed)

        for i in range(count):
            ang = rng.uniform(0.0, 2.0 * math.pi)
            speed = rng.uniform(30.0, 90.0)
            dist_t = speed * t - 15.0 * t * t
            if dist_t <= 0.0:
                continue
            x1 = origin[0] + math.cos(ang) * max(0.0, dist_t - 8.0)
            y1 = origin[1] + math.sin(ang) * max(0.0, dist_t - 8.0)
            x2 = origin[0] + math.cos(ang) * dist_t
            y2 = origin[1] + math.sin(ang) * dist_t
            c.line((x1, y1), (x2, y2), col=col, w=2.0)

    @staticmethod
    def smoke(frame_obj: Any, origin: Point, t: float, count: int = 8, seed: int = 42) -> None:
        """Puffs of wobbly cartoon smoke rising and expanding."""
        c = frame_obj
        rng = random.Random(seed)

        for i in range(count):
            age = max(0.0, t - i * 0.15)
            if age <= 0.0:
                continue
            rad = 4.0 + age * 16.0
            drift_x = rng.uniform(-10.0, 10.0) * age
            rise_y = -35.0 * age
            c.circle((origin[0] + drift_x, origin[1] + rise_y), rad, col=(180, 180, 190), w=2.0)

    @staticmethod
    def rain(frame_obj: Any, box: Tuple[float, float, float, float], t: float, count: int = 30, seed: int = 42) -> None:
        """Angled raindrops falling across the stage."""
        c = frame_obj
        bx, by, bw, bh = box
        rng = random.Random(seed)

        for i in range(count):
            init_x = rng.uniform(bx, bx + bw)
            init_y = rng.uniform(by, by + bh)
            # Falling trajectory
            rx = bx + (init_x + t * 80.0) % bw
            ry = by + (init_y + t * 240.0) % bh
            c.line((rx, ry), (rx - 4.0, ry + 12.0), col=(80, 220, 255), w=1.5)


def draw_speed_lines(
    frame_obj: Any,
    direction: str = "right",
    intensity: float = 1.0,
    count: int = 14,
    col: Tuple[int, int, int] = (160, 160, 170)
) -> None:
    """Draw comic action speed lines across edges."""
    c = frame_obj
    rng = random.Random(int(frame_obj.f * 97))

    for _ in range(int(count * intensity)):
        if direction in ("right", "left"):
            y = rng.uniform(40.0, 320.0)
            x_start = rng.uniform(0.0, 120.0) if direction == "right" else rng.uniform(520.0, 640.0)
            length = rng.uniform(40.0, 160.0)
            x_end = x_start + length if direction == "right" else x_start - length
            c.line((x_start, y), (x_end, y), col=col, w=1.8)
        else:
            x = rng.uniform(40.0, 600.0)
            y_start = rng.uniform(0.0, 100.0) if direction == "down" else rng.uniform(260.0, 360.0)
            length = rng.uniform(40.0, 140.0)
            y_end = y_start + length if direction == "down" else y_start - length
            c.line((x, y_start), (x, y_end), col=col, w=1.8)


# ------------------------------------------------------------------ 4. Virtual Camera
class Camera:
    """
    2D virtual camera supporting smooth pan, zoom, shake, and parallax layers.
    Maps world coordinates to logical canvas coordinates (standard canvas: 640x360).
    """
    def __init__(self, cx: float = 320.0, cy: float = 180.0, zoom: float = 1.0):
        self.cx = cx
        self.cy = cy
        self.zoom = zoom
        self.shake_amplitude = 0.0
        self.shake_freq = 15.0

    def look_at(self, x: float, y: float, zoom: Optional[float] = None) -> None:
        self.cx = x
        self.cy = y
        if zoom is not None:
            self.zoom = zoom

    def add_shake(self, amplitude: float = 4.0, freq: float = 18.0) -> None:
        self.shake_amplitude = amplitude
        self.shake_freq = freq

    def world_to_screen(self, pt: Point, z: float = 1.0, t: float = 0.0) -> Point:
        """
        Transform world coordinate (wx, wy) into screen space with depth factor z (parallax).
        z = 1.0: normal gameplay/stage layer.
        z = 0.4: far background (moves slower).
        z = 1.4: foreground (moves faster).
        """
        # Camera shake
        sx = 0.0
        sy = 0.0
        if self.shake_amplitude > 0.0:
            sx = math.sin(t * self.shake_freq * 1.3) * self.shake_amplitude
            sy = math.cos(t * self.shake_freq) * self.shake_amplitude

        cam_x = self.cx + sx
        cam_y = self.cy + sy

        # Parallax offset relative to world center (320, 180)
        eff_zoom = 1.0 + (self.zoom - 1.0) * z
        rel_x = (pt[0] - (320.0 + (cam_x - 320.0) * z)) * eff_zoom
        rel_y = (pt[1] - (180.0 + (cam_y - 180.0) * z)) * eff_zoom

        return (320.0 + rel_x, 180.0 + rel_y)


# ------------------------------------------------------------------ 5. Transitions
def transition_wipe(img_a: Image.Image, img_b: Image.Image, progress: float, direction: str = "left") -> Image.Image:
    """Hand-drawn edge wipe transition from img_a to img_b."""
    w, h = img_a.size
    p = max(0.0, min(1.0, progress))
    out = img_a.copy()

    split_x = int(w * p)
    if direction == "left":
        # Wipes from right to left
        crop_box = (w - split_x, 0, w, h)
        out.paste(img_b.crop(crop_box), (w - split_x, 0))
    else:
        # Wipes from left to right
        crop_box = (0, 0, split_x, h)
        out.paste(img_b.crop(crop_box), (0, 0))
    return out


def transition_iris(img_a: Image.Image, img_b: Image.Image, progress: float) -> Image.Image:
    """Circular aperture iris transition revealing img_b."""
    w, h = img_a.size
    p = max(0.0, min(1.0, progress))
    max_r = math.hypot(w / 2.0, h / 2.0)
    cur_r = max_r * p

    mask = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(mask)
    cx, cy = w / 2.0, h / 2.0
    d.ellipse([cx - cur_r, cy - cur_r, cx + cur_r, cy + cur_r], fill=255)

    out = img_a.copy()
    out.paste(img_b, (0, 0), mask)
    return out


def transition_ink_splash(img_a: Image.Image, img_b: Image.Image, progress: float, seed: int = 42) -> Image.Image:
    """Organic sketchy ink splatter expanding from center."""
    w, h = img_a.size
    p = max(0.0, min(1.0, progress))
    mask = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(mask)
    cx, cy = w / 2.0, h / 2.0

    rng = random.Random(seed)
    max_r = math.hypot(w / 2.0, h / 2.0) * 1.1 * p
    n_pts = 32
    poly = []
    for i in range(n_pts):
        ang = (2.0 * math.pi * i) / n_pts
        r = max_r * (0.8 + 0.4 * rng.uniform(0.0, 1.0))
        poly.append((cx + math.cos(ang) * r, cy + math.sin(ang) * r))

    if poly and p > 0.05:
        d.polygon(poly, fill=255)

    out = img_a.copy()
    out.paste(img_b, (0, 0), mask)
    return out
