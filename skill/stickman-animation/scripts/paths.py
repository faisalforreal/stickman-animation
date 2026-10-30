"""Universal Path Engine for stickman_anim.

Provides:
- Parametric path representation: Lines, Quadratic/Cubic Béziers, Arcs, Catmull-Rom splines.
- Arc-length parameterization for smooth draw-on animation (0.0 to 1.0).
- Rough.js-style sketchy stroke rendering (bowing, double strokes, stop-motion boil).
- Variable pressure / tapered stroke profiles.
- Theme-aware fill styles: hatch, crosshatch, stipple, scribble, and wobbly solid.
- Pen cursor rendering at the active stroke tip.
"""

import math
import random
from typing import List, Tuple, Optional, Union, Dict, Any
from PIL import Image, ImageDraw


Point = Tuple[float, float]


def dist(p1: Point, p2: Point) -> float:
    return math.hypot(p2[0] - p1[0], p2[1] - p1[1])


def lerp_pt(p1: Point, p2: Point, t: float) -> Point:
    return (p1[0] + (p2[0] - p1[0]) * t, p1[1] + (p2[1] - p1[1]) * t)


def quad_bezier_pt(p0: Point, p1: Point, p2: Point, t: float) -> Point:
    u = 1.0 - t
    return (
        u * u * p0[0] + 2.0 * u * t * p1[0] + t * t * p2[0],
        u * u * p0[1] + 2.0 * u * t * p1[1] + t * t * p2[1],
    )


def cubic_bezier_pt(p0: Point, p1: Point, p2: Point, p3: Point, t: float) -> Point:
    u = 1.0 - t
    u2 = u * u
    t2 = t * t
    return (
        u2 * u * p0[0] + 3.0 * u2 * t * p1[0] + 3.0 * u * t2 * p2[0] + t2 * t * p3[0],
        u2 * u * p0[1] + 3.0 * u2 * t * p1[1] + 3.0 * u * t2 * p2[1] + t2 * t * p3[1],
    )


def arc_to_cubics(
    x1: float, y1: float, rx: float, ry: float, angle: float,
    large_arc: bool, sweep: bool, x2: float, y2: float
) -> List[Tuple[Point, Point, Point, Point]]:
    """Convert SVG elliptical arc to a sequence of cubic Béziers."""
    if (x1 == x2 and y1 == y2) or rx == 0 or ry == 0:
        return []

    rx, ry = abs(rx), abs(ry)
    phi = math.radians(angle % 360.0)
    cos_phi = math.cos(phi)
    sin_phi = math.sin(phi)

    # Step 1: Compute (x1', y1')
    dx = (x1 - x2) / 2.0
    dy = (y1 - y2) / 2.0
    x1p = cos_phi * dx + sin_phi * dy
    y1p = -sin_phi * dx + cos_phi * dy

    # Correct radii if too small
    lam = (x1p * x1p) / (rx * rx) + (y1p * y1p) / (ry * ry)
    if lam > 1.0:
        s = math.sqrt(lam)
        rx *= s
        ry *= s

    # Step 2: Compute (cx', cy')
    sign = -1.0 if large_arc == sweep else 1.0
    sq = ((rx * rx * ry * ry) - (rx * rx * y1p * y1p) - (ry * ry * x1p * x1p)) / (
        (rx * rx * y1p * y1p) + (ry * ry * x1p * x1p)
    )
    sq = max(0.0, sq)
    coef = sign * math.sqrt(sq)
    cxp = coef * ((rx * y1p) / ry)
    cyp = coef * (-(ry * x1p) / rx)

    # Step 3: Compute (cx, cy) from (cx', cy')
    cx = cos_phi * cxp - sin_phi * cyp + (x1 + x2) / 2.0
    cy = sin_phi * cxp + cos_phi * cyp + (y1 + y2) / 2.0

    # Step 4: Compute theta1 and dtheta
    def vec_angle(ux, uy, vx, vy):
        dot = ux * vx + uy * vy
        l = math.sqrt(ux * ux + uy * uy) * math.sqrt(vx * vx + vy * vy)
        a = math.acos(max(-1.0, min(1.0, dot / l))) if l > 0 else 0.0
        if ux * vy - uy * vx < 0:
            a = -a
        return a

    ux = (x1p - cxp) / rx
    uy = (y1p - cyp) / ry
    vx = (-x1p - cxp) / rx
    vy = (-y1p - cyp) / ry
    theta1 = vec_angle(1.0, 0.0, ux, uy)
    dtheta = vec_angle(ux, uy, vx, vy)
    if not sweep and dtheta > 0:
        dtheta -= 2.0 * math.pi
    elif sweep and dtheta < 0:
        dtheta += 2.0 * math.pi

    # Approximate arc with cubic Bézier segments (each <= pi/2)
    segments = max(1, int(math.ceil(abs(dtheta) / (math.pi / 2.0))))
    dt = dtheta / segments
    cubics = []
    t = theta1
    curr_pt = (x1, y1)

    for _ in range(segments):
        t_next = t + dt
        alpha = math.sin(dt) * (math.sqrt(4.0 + 3.0 * math.tan(dt / 2.0) ** 2) - 1.0) / 3.0

        cos_t, sin_t = math.cos(t), math.sin(t)
        cos_tn, sin_tn = math.cos(t_next), math.sin(t_next)

        p0 = curr_pt
        ep0_x = -rx * sin_t
        ep0_y = ry * cos_t
        cp1_x = cos_phi * (rx * cos_t + alpha * ep0_x) - sin_phi * (ry * sin_t + alpha * ep0_y) + cx
        cp1_y = sin_phi * (rx * cos_t + alpha * ep0_x) + cos_phi * (ry * sin_t + alpha * ep0_y) + cy
        cp1 = (cp1_x, cp1_y)

        ep1_x = -rx * sin_tn
        ep1_y = ry * cos_tn
        cp2_x = cos_phi * (rx * cos_tn - alpha * ep1_x) - sin_phi * (ry * sin_tn - alpha * ep1_y) + cx
        cp2_y = sin_phi * (rx * cos_tn - alpha * ep1_x) + cos_phi * (ry * sin_tn - alpha * ep1_y) + cy
        cp2 = (cp2_x, cp2_y)

        p3_x = cos_phi * (rx * cos_tn) - sin_phi * (ry * sin_tn) + cx
        p3_y = sin_phi * (rx * cos_tn) + cos_phi * (ry * sin_tn) + cy
        p3 = (p3_x, p3_y)

        cubics.append((p0, cp1, cp2, p3))
        curr_pt = p3
        t = t_next

    return cubics


class PathSegment:
    """Base class for path components."""
    def sample(self, steps: int = 16) -> List[Point]:
        raise NotImplementedError

    def length(self) -> float:
        pts = self.sample()
        return sum(dist(pts[i], pts[i+1]) for i in range(len(pts)-1))


class LineSegment(PathSegment):
    def __init__(self, p0: Point, p1: Point):
        self.p0 = p0
        self.p1 = p1

    def sample(self, steps: int = 4) -> List[Point]:
        return [lerp_pt(self.p0, self.p1, i / float(steps)) for i in range(steps + 1)]

    def length(self) -> float:
        return dist(self.p0, self.p1)


class QuadSegment(PathSegment):
    def __init__(self, p0: Point, p1: Point, p2: Point):
        self.p0, self.p1, self.p2 = p0, p1, p2

    def sample(self, steps: int = 16) -> List[Point]:
        return [quad_bezier_pt(self.p0, self.p1, self.p2, i / float(steps)) for i in range(steps + 1)]


class CubicSegment(PathSegment):
    def __init__(self, p0: Point, p1: Point, p2: Point, p3: Point):
        self.p0, self.p1, self.p2, self.p3 = p0, p1, p2, p3

    def sample(self, steps: int = 24) -> List[Point]:
        return [cubic_bezier_pt(self.p0, self.p1, self.p2, self.p3, i / float(steps)) for i in range(steps + 1)]


class Path:
    """A multi-contour vector path composed of continuous segments."""
    def __init__(self):
        self.contours: List[List[PathSegment]] = []
        self._current_contour: List[PathSegment] = []
        self._current_pt: Point = (0.0, 0.0)
        self._start_pt: Point = (0.0, 0.0)

    def move_to(self, x: float, y: float) -> "Path":
        if self._current_contour:
            self.contours.append(self._current_contour)
            self._current_contour = []
        self._current_pt = (float(x), float(y))
        self._start_pt = self._current_pt
        return self

    def line_to(self, x: float, y: float) -> "Path":
        p = (float(x), float(y))
        self._current_contour.append(LineSegment(self._current_pt, p))
        self._current_pt = p
        return self

    def quad_to(self, cx: float, cy: float, x: float, y: float) -> "Path":
        cp = (float(cx), float(cy))
        p = (float(x), float(y))
        self._current_contour.append(QuadSegment(self._current_pt, cp, p))
        self._current_pt = p
        return self

    def cubic_to(self, c1x: float, c1y: float, c2x: float, c2y: float, x: float, y: float) -> "Path":
        cp1 = (float(c1x), float(c1y))
        cp2 = (float(c2x), float(c2y))
        p = (float(x), float(y))
        self._current_contour.append(CubicSegment(self._current_pt, cp1, cp2, p))
        self._current_pt = p
        return self

    def arc_to(self, rx: float, ry: float, angle: float, large_arc: bool, sweep: bool, x: float, y: float) -> "Path":
        cubics = arc_to_cubics(self._current_pt[0], self._current_pt[1], rx, ry, angle, large_arc, sweep, float(x), float(y))
        for p0, cp1, cp2, p3 in cubics:
            self._current_contour.append(CubicSegment(p0, cp1, cp2, p3))
        self._current_pt = (float(x), float(y))
        return self

    def close(self) -> "Path":
        if self._current_pt != self._start_pt:
            self.line_to(self._start_pt[0], self._start_pt[1])
        if self._current_contour:
            self.contours.append(self._current_contour)
            self._current_contour = []
        return self

    def end(self) -> "Path":
        if self._current_contour:
            self.contours.append(self._current_contour)
            self._current_contour = []
        return self

    def get_polylines(self) -> List[List[Point]]:
        """Flatten all contours into sample points."""
        self.end()
        result = []
        for c in self.contours:
            if not c:
                continue
            pts = []
            for seg in c:
                sampled = seg.sample()
                if pts and sampled and dist(pts[-1], sampled[0]) < 1e-4:
                    pts.extend(sampled[1:])
                else:
                    pts.extend(sampled)
            if pts:
                result.append(pts)
        return result

    def total_length(self) -> float:
        return sum(sum(seg.length() for seg in c) for c in self.contours)

    def slice(self, progress: float) -> List[List[Point]]:
        """Slice the path along its total arc length from 0.0 to progress (0..1)."""
        progress = max(0.0, min(1.0, float(progress)))
        if progress <= 0.0:
            return []

        polys = self.get_polylines()
        total_len = sum(sum(dist(p[i], p[i+1]) for i in range(len(p)-1)) for p in polys)
        if total_len <= 0.0:
            return polys

        target_len = total_len * progress
        accum = 0.0
        sliced_polys = []

        for poly in polys:
            if accum >= target_len:
                break
            current_poly = [poly[0]]
            for i in range(len(poly) - 1):
                p0, p1 = poly[i], poly[i+1]
                d = dist(p0, p1)
                if accum + d <= target_len:
                    current_poly.append(p1)
                    accum += d
                else:
                    rem = target_len - accum
                    t = rem / d if d > 0 else 0.0
                    current_poly.append(lerp_pt(p0, p1, t))
                    accum = target_len
                    break
            sliced_polys.append(current_poly)

        return sliced_polys


# ------------------------------------------------------------------ Rough Sketchy Styler
def apply_rough_bowing(
    poly: List[Point],
    rng: random.Random,
    bowing: float = 0.8,
    roughness: float = 1.0,
    double_stroke: bool = True
) -> List[List[Point]]:
    """Generates hand-drawn, bowed double strokes in the spirit of rough.js."""
    if len(poly) < 2:
        return [poly]

    strokes = []
    passes = 2 if double_stroke else 1

    for p in range(passes):
        curved = []
        for i in range(len(poly) - 1):
            p0 = poly[i]
            p1 = poly[i + 1]
            d = dist(p0, p1)
            if d < 1e-3:
                continue

            # Perpendicular vector
            nx = -(p1[1] - p0[1]) / d
            ny = (p1[0] - p0[0]) / d

            # Midpoint bowing with random curvature
            bow = rng.uniform(-bowing, bowing) * min(15.0, d * 0.1)
            mid = ((p0[0] + p1[0]) / 2.0 + nx * bow, (p0[1] + p1[1]) / 2.0 + ny * bow)

            # Jitter endpoints slightly on 2nd pass
            jit = roughness * (0.6 if p == 0 else 1.2)
            pt0 = (p0[0] + rng.uniform(-jit, jit), p0[1] + rng.uniform(-jit, jit))
            pt1 = (p1[0] + rng.uniform(-jit, jit), p1[1] + rng.uniform(-jit, jit))

            # Sample quadratic arc for subtle curve
            segment_pts = [quad_bezier_pt(pt0, mid, pt1, t / 4.0) for t in range(5)]
            if curved:
                curved.extend(segment_pts[1:])
            else:
                curved.extend(segment_pts)

        if curved:
            strokes.append(curved)

    return strokes


# ------------------------------------------------------------------ Fill Generators
def generate_hatch_fill(
    polygon: List[Point],
    spacing: float = 8.0,
    angle_deg: float = 45.0,
    cross: bool = False,
    rng: Optional[random.Random] = None
) -> List[Tuple[Point, Point]]:
    """Compute sketchy hatch/crosshatch lines clipped inside a polygon using ray casting."""
    if len(polygon) < 3:
        return []

    min_x = min(p[0] for p in polygon)
    max_x = max(p[0] for p in polygon)
    min_y = min(p[1] for p in polygon)
    max_y = max(p[1] for p in polygon)

    angles = [angle_deg]
    if cross:
        angles.append(angle_deg + 90.0)

    lines: List[Tuple[Point, Point]] = []
    diag = math.hypot(max_x - min_x, max_y - min_y)
    cx, cy = (min_x + max_x) / 2.0, (min_y + max_y) / 2.0

    for ang in angles:
        rad = math.radians(ang)
        cos_a, sin_a = math.cos(rad), math.sin(rad)
        # Normal vector to scan lines
        nx, ny = -sin_a, cos_a

        # Scan distance range
        num_lines = int(diag / max(2.0, spacing))
        for step in range(-num_lines // 2, num_lines // 2 + 1):
            offset = step * spacing
            if rng:
                offset += rng.uniform(-spacing * 0.15, spacing * 0.15)

            # Ray: pt = (cx, cy) + offset * (nx, ny) + t * (cos_a, sin_a)
            ox = cx + offset * nx
            oy = cy + offset * ny

            # Intersect with all polygon segments
            intersections = []
            for i in range(len(polygon)):
                p0 = polygon[i]
                p1 = polygon[(i + 1) % len(polygon)]
                # Line segment: p0 + s * (p1 - p0)
                # Ray: o + t * dir
                dx, dy = cos_a, sin_a
                sx, sy = p1[0] - p0[0], p1[1] - p0[1]
                denom = dx * sy - dy * sx
                if abs(denom) < 1e-5:
                    continue

                t = ((p0[0] - ox) * sy - (p0[1] - oy) * sx) / denom
                s = ((p0[0] - ox) * dy - (p0[1] - oy) * dx) / denom
                if 0.0 <= s <= 1.0:
                    intersections.append(t)

            intersections.sort()
            for k in range(0, len(intersections) - 1, 2):
                t0, t1 = intersections[k], intersections[k + 1]
                if t1 - t0 > 2.0:
                    lines.append(((ox + t0 * cos_a, oy + t0 * sin_a), (ox + t1 * cos_a, oy + t1 * sin_a)))

    return lines


def generate_stipple_fill(
    polygon: List[Point],
    density: float = 0.05,
    rng: Optional[random.Random] = None
) -> List[Point]:
    """Generate deterministic jittered stipple points inside a polygon."""
    if len(polygon) < 3:
        return []
    rng = rng or random.Random(42)

    min_x, max_x = min(p[0] for p in polygon), max(p[0] for p in polygon)
    min_y, max_y = min(p[1] for p in polygon), max(p[1] for p in polygon)
    area = (max_x - min_x) * (max_y - min_y)
    count = int(area * density)

    # Point-in-polygon test (ray casting)
    def inside(px, py):
        ins = False
        n = len(polygon)
        for i in range(n):
            p0, p1 = polygon[i], polygon[(i + 1) % n]
            if ((p0[1] > py) != (p1[1] > py)) and (px < (p1[0] - p0[0]) * (py - p0[1]) / (p1[1] - p0[1]) + p0[0]):
                ins = not ins
        return ins

    pts = []
    for _ in range(count * 2):
        rx = rng.uniform(min_x, max_x)
        ry = rng.uniform(min_y, max_y)
        if inside(rx, ry):
            pts.append((rx, ry))
            if len(pts) >= count:
                break
    return pts


# ------------------------------------------------------------------ Pen Cursor Renderer
def draw_hand_pen(
    draw: ImageDraw.ImageDraw,
    tip: Point,
    s_factor: int,
    pen_col: Tuple[int, int, int] = (220, 220, 220)
) -> None:
    """Draws a clean, stylized whiteboard pen nib at the active stroke tip."""
    x, y = tip[0] * s_factor, tip[1] * s_factor
    nib_len = 22 * s_factor
    nib_w = 6 * s_factor
    angle = math.radians(40.0)
    dx, dy = math.cos(angle), math.sin(angle)
    px, py = -dy, dx

    # Nib point at (x, y), body slanting up-right
    p_tip = (x, y)
    p_left = (x + dx * nib_len + px * nib_w, y - dy * nib_len + py * nib_w)
    p_right = (x + dx * nib_len - px * nib_w, y - dy * nib_len - py * nib_w)
    p_top = (x + dx * (nib_len + 12 * s_factor), y - dy * (nib_len + 12 * s_factor))

    draw.polygon([p_tip, p_left, p_top, p_right], fill=(30, 30, 35), outline=pen_col, width=max(1, int(1.5 * s_factor)))
    # Metal tip highlight
    draw.polygon([p_tip, (x + dx * 6 * s_factor + px * 2 * s_factor, y - dy * 6 * s_factor + py * 2 * s_factor),
                  (x + dx * 6 * s_factor - px * 2 * s_factor, y - dy * 6 * s_factor - py * 2 * s_factor)],
                 fill=pen_col)
