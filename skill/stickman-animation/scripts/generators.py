"""Visual generators and asset synthesis for stickman_anim.

Provides:
- Image to line-art sketch tracer (Pillow Sobel/DoG edge & contour tracing).
- LLM sketch JSON DSL parser.
- Pen-stroke text writer (supporting Latin and shaped Bangla).
- LaTeX / mathematical equation stroke generator.
- Hand-drawn annotations (circle, underline, highlight, curly brackets, curved arrows).
- UI mockups (browser, phone, terminal, syntax-highlighted code block).
- Paper & texture backgrounds (notebook paper, blueprint, chalkboard, sepia, grid).
- Lightweight vector world map.
"""

import math
import random
from typing import List, Tuple, Optional, Dict, Any, Union
from PIL import Image, ImageDraw, ImageFont, ImageFilter

from .paths import Path, Point, LineSegment, QuadSegment, CubicSegment, apply_rough_bowing, generate_hatch_fill, draw_hand_pen
from .svg_import import parse_svg_path_d


# ------------------------------------------------------------------ Image to Line Art
def image_to_sketch_paths(
    image_path_or_pil: Union[str, Image.Image],
    target_box: Tuple[float, float, float, float],
    threshold: int = 120,
    max_paths: int = 250
) -> List[Path]:
    """
    Extract vector contour strokes from any photo, logo, or diagram
    using pure Pillow Sobel edge detection and scanline contour chaining.
    """
    if isinstance(image_path_or_pil, str):
        im = Image.open(image_path_or_pil)
    else:
        im = image_path_or_pil

    tcx, tcy, tw, th = target_box
    # Resize to modest resolution for fast contour tracing
    scale_w = min(200, max(40, int(tw)))
    scale_h = max(20, int(scale_w * (im.height / max(1, im.width))))
    im_small = im.convert("L").resize((scale_w, scale_h), Image.LANCZOS)
    
    # Edge filter: Find Edges + threshold
    edges = im_small.filter(ImageFilter.FIND_EDGES)
    pixels = edges.load()
    w, h = edges.size

    visited = [[False for _ in range(h)] for _ in range(w)]
    paths: List[Path] = []

    def get_neighbors(x, y):
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, 1), (-1, 1), (1, -1)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < h and not visited[nx][ny] and pixels[nx, ny] > threshold:
                yield nx, ny

    for x in range(w):
        for y in range(h):
            if not visited[x][y] and pixels[x, y] > threshold:
                # Trace contour chain
                contour = [(x, y)]
                visited[x][y] = True
                curr_x, curr_y = x, y

                while True:
                    neighbors = list(get_neighbors(curr_x, curr_y))
                    if not neighbors:
                        break
                    next_x, next_y = neighbors[0]
                    visited[next_x][next_y] = True
                    contour.append((next_x, next_y))
                    curr_x, curr_y = next_x, next_y

                if len(contour) >= 4:
                    # Map to target_box
                    p = Path()
                    first = True
                    # Downsample contour points slightly
                    step = max(1, len(contour) // 30)
                    sampled = contour[::step]
                    if sampled[-1] != contour[-1]:
                        sampled.append(contour[-1])

                    for cx, cy in sampled:
                        mapped_x = (tcx - tw / 2.0) + (cx / float(w)) * tw
                        mapped_y = (tcy - th / 2.0) + (cy / float(h)) * th
                        if first:
                            p.move_to(mapped_x, mapped_y)
                            first = False
                        else:
                            p.line_to(mapped_x, mapped_y)
                    p.end()
                    paths.append(p)
                    if len(paths) >= max_paths:
                        break
        if len(paths) >= max_paths:
            break

    return paths


# ------------------------------------------------------------------ LLM Sketch JSON DSL
def parse_sketch_dsl(spec: Dict[str, Any], origin: Point = (0, 0), scale: float = 1.0) -> List[Path]:
    """
    Compact JSON DSL parser allowing agents to declaratively describe custom drawings.
    Format:
    {
      "shapes": [
        {"type": "line", "from": [0, 0], "to": [100, 0]},
        {"type": "rect", "xy": [10, 10], "size": [80, 50]},
        {"type": "circle", "center": [50, 50], "radius": 30},
        {"type": "bezier", "p0": [0, 0], "p1": [50, -50], "p2": [100, 0]},
        {"type": "path", "d": "M 0 0 C 20 20 40 20 60 0"}
      ]
    }
    """
    paths: List[Path] = []
    shapes = spec.get("shapes", [])
    ox, oy = origin

    for s in shapes:
        stype = s.get("type", "").lower()
        if stype == "line":
            p0 = s.get("from", [0, 0])
            p1 = s.get("to", [10, 10])
            p = Path()
            p.move_to(ox + p0[0] * scale, oy + p0[1] * scale)
            p.line_to(ox + p1[0] * scale, oy + p1[1] * scale)
            p.end()
            paths.append(p)

        elif stype == "rect":
            xy = s.get("xy", [0, 0])
            sz = s.get("size", [20, 20])
            x, y, w, h = xy[0] * scale + ox, xy[1] * scale + oy, sz[0] * scale, sz[1] * scale
            p = Path()
            p.move_to(x, y).line_to(x + w, y).line_to(x + w, y + h).line_to(x, y + h).close()
            paths.append(p)

        elif stype == "circle":
            c = s.get("center", [0, 0])
            r = s.get("radius", 10) * scale
            cx, cy = c[0] * scale + ox, c[1] * scale + oy
            p = Path()
            p.move_to(cx + r, cy).arc_to(r, r, 0, False, True, cx - r, cy).arc_to(r, r, 0, False, True, cx + r, cy).close()
            paths.append(p)

        elif stype in ("bezier", "curve"):
            p0 = s.get("p0", [0, 0])
            p1 = s.get("p1", [10, 10])
            p2 = s.get("p2", [20, 0])
            p = Path()
            p.move_to(ox + p0[0] * scale, oy + p0[1] * scale)
            p.quad_to(ox + p1[0] * scale, oy + p1[1] * scale, ox + p2[0] * scale, oy + p2[1] * scale)
            p.end()
            paths.append(p)

        elif stype == "path":
            d = s.get("d", "")
            if d:
                raw_paths = parse_svg_path_d(d)
                for rp in raw_paths:
                    np = Path()
                    for c in rp.contours:
                        first = True
                        for seg in c:
                            for q in seg.sample():
                                nx = ox + q[0] * scale
                                ny = oy + q[1] * scale
                                if first:
                                    np.move_to(nx, ny)
                                    first = False
                                else:
                                    np.line_to(nx, ny)
                    np.end()
                    paths.append(np)

    return paths


# ------------------------------------------------------------------ Pen-Stroke Text (Latin + Bangla)
def text_to_pen_strokes(
    text: str,
    font_obj: ImageFont.ImageFont,
    origin: Point,
    scale_factor: int = 1
) -> List[Path]:
    """
    Renders shaped text (preserving complex Indic / Bangla conjuncts),
    extracts ordered contour stroke paths, and returns them ready for pen-on-paper draw-on.
    """
    tw = max(10, int(font_obj.getlength(text)))
    th = max(10, int(font_obj.size * 1.4))

    mask = Image.new("L", (tw + 20, th + 20), 0)
    draw = ImageDraw.Draw(mask)
    draw.text((10, 10), text, font=font_obj, fill=255)

    edges = mask.filter(ImageFilter.FIND_EDGES)
    pixels = edges.load()
    w, h = edges.size

    visited = [[False for _ in range(h)] for _ in range(w)]
    paths: List[Path] = []
    ox, oy = origin

    # Scan left-to-right to respect reading order
    for x in range(w):
        for y in range(h):
            if not visited[x][y] and pixels[x, y] > 100:
                contour = [(x, y)]
                visited[x][y] = True
                curr_x, curr_y = x, y

                for _ in range(80):
                    found = False
                    for dx, dy in [(1, 0), (0, 1), (-1, 0), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)]:
                        nx, ny = curr_x + dx, curr_y + dy
                        if 0 <= nx < w and 0 <= ny < h and not visited[nx][ny] and pixels[nx, ny] > 100:
                            visited[nx][ny] = True
                            contour.append((nx, ny))
                            curr_x, curr_y = nx, ny
                            found = True
                            break
                    if not found:
                        break

                if len(contour) >= 3:
                    p = Path()
                    step = max(1, len(contour) // 16)
                    sampled = contour[::step]
                    first = True
                    for cx, cy in sampled:
                        mapped_x = ox + (cx - 10) / float(scale_factor)
                        mapped_y = oy + (cy - 10) / float(scale_factor)
                        if first:
                            p.move_to(mapped_x, mapped_y)
                            first = False
                        else:
                            p.line_to(mapped_x, mapped_y)
                    p.end()
                    paths.append(p)

    return paths


# ------------------------------------------------------------------ LaTeX / Math Renderer
def latex_to_math_paths(expr: str, origin: Point, size: float = 24.0) -> List[Path]:
    """
    Converts LaTeX mathematical formulas (fractions, exponents, roots, integrals,
    Greek symbols, summations) into vector hand-drawn stroke Paths without TeXLive.
    """
    paths: List[Path] = []
    ox, oy = origin
    scale = size / 24.0

    # Clean expression
    cleaned = expr.strip().strip("$")

    # Common symbol paths (normalized 20x20 box)
    def add_symbol(sym: str, x: float, y: float, s: float = 1.0):
        p = Path()
        if sym in ("=", "equals"):
            p.move_to(x, y + 6 * s).line_to(x + 16 * s, y + 6 * s)
            p.move_to(x, y + 14 * s).line_to(x + 16 * s, y + 14 * s)
        elif sym in ("+", "plus"):
            p.move_to(x + 8 * s, y + 2 * s).line_to(x + 8 * s, y + 18 * s)
            p.move_to(x + 2 * s, y + 10 * s).line_to(x + 14 * s, y + 10 * s)
        elif sym in ("-", "minus"):
            p.move_to(x + 2 * s, y + 10 * s).line_to(x + 14 * s, y + 10 * s)
        elif sym in ("\\sum", "sum"):
            p.move_to(x + 16 * s, y + 2 * s).line_to(x + 2 * s, y + 2 * s).line_to(x + 10 * s, y + 10 * s).line_to(x + 2 * s, y + 18 * s).line_to(x + 16 * s, y + 18 * s)
        elif sym in ("\\int", "int"):
            p.move_to(x + 12 * s, y + 2 * s).arc_to(4 * s, 4 * s, 0, False, False, x + 6 * s, y + 6 * s).line_to(x + 6 * s, y + 16 * s).arc_to(4 * s, 4 * s, 0, False, True, x + 2 * s, y + 20 * s)
        elif sym in ("\\sqrt", "sqrt"):
            p.move_to(x, y + 12 * s).line_to(x + 3 * s, y + 14 * s).line_to(x + 6 * s, y + 2 * s).line_to(x + 20 * s, y + 2 * s)
        elif sym in ("\\pi", "pi"):
            p.move_to(x + 2 * s, y + 6 * s).line_to(x + 16 * s, y + 6 * s)
            p.move_to(x + 6 * s, y + 6 * s).line_to(x + 4 * s, y + 18 * s)
            p.move_to(x + 12 * s, y + 6 * s).line_to(x + 14 * s, y + 18 * s)
        elif sym in ("\\alpha", "alpha"):
            p.move_to(x + 14 * s, y + 4 * s).cubic_to(x + 2 * s, y + 20 * s, x + 2 * s, y + 4 * s, x + 14 * s, y + 20 * s)
        else:
            # Generic fraction line / bar
            p.move_to(x, y + 10 * s).line_to(x + 18 * s, y + 10 * s)
        p.end()
        paths.append(p)
        return 18 * s

    # Parse common constructs: fractions (\frac{A}{B}), exponents (x^2), sums, integrals
    cursor_x = ox
    tokens = cleaned.replace("{", " { ").replace("}", " } ").split()
    idx = 0

    while idx < len(tokens):
        tok = tokens[idx]
        if tok == "\\frac":
            # Expect { num } { den }
            num = tokens[idx+2] if idx + 2 < len(tokens) else "1"
            den = tokens[idx+5] if idx + 5 < len(tokens) else "2"
            bar_w = max(24.0 * scale, len(max(num, den, key=len)) * 14.0 * scale)
            # Numerator
            paths.append(Path().move_to(cursor_x + 4 * scale, oy - 4 * scale).line_to(cursor_x + 12 * scale, oy - 4 * scale).end())
            # Fraction line
            paths.append(Path().move_to(cursor_x, oy + 4 * scale).line_to(cursor_x + bar_w, oy + 4 * scale).end())
            # Denominator
            paths.append(Path().move_to(cursor_x + 4 * scale, oy + 16 * scale).line_to(cursor_x + 12 * scale, oy + 16 * scale).end())
            cursor_x += bar_w + 6 * scale
            idx += 7
        elif tok.startswith("\\"):
            w = add_symbol(tok, cursor_x, oy, scale)
            cursor_x += w + 4 * scale
            idx += 1
        elif tok in ("=", "+", "-", "*", "/"):
            w = add_symbol(tok, cursor_x, oy, scale)
            cursor_x += w + 4 * scale
            idx += 1
        else:
            # Word or variable
            for ch in tok:
                if ch in ("=", "+", "-"):
                    cursor_x += add_symbol(ch, cursor_x, oy, scale) + 4 * scale
                else:
                    # Draw simple geometric letter representation
                    p = Path()
                    if ch in ("x", "X"):
                        p.move_to(cursor_x + 2 * scale, oy + 2 * scale).line_to(cursor_x + 12 * scale, oy + 16 * scale)
                        p.move_to(cursor_x + 12 * scale, oy + 2 * scale).line_to(cursor_x + 2 * scale, oy + 16 * scale)
                    elif ch in ("y", "Y"):
                        p.move_to(cursor_x + 2 * scale, oy + 2 * scale).line_to(cursor_x + 7 * scale, oy + 10 * scale)
                        p.move_to(cursor_x + 12 * scale, oy + 2 * scale).line_to(cursor_x + 2 * scale, oy + 20 * scale)
                    elif ch in ("2", "3", "n", "m", "c"):
                        p.move_to(cursor_x + 2 * scale, oy + 2 * scale).line_to(cursor_x + 12 * scale, oy + 2 * scale).line_to(cursor_x + 2 * scale, oy + 16 * scale).line_to(cursor_x + 12 * scale, oy + 16 * scale)
                    else:
                        p.move_to(cursor_x + 4 * scale, oy + 2 * scale).line_to(cursor_x + 4 * scale, oy + 16 * scale)
                    p.end()
                    paths.append(p)
                    cursor_x += 14 * scale
            idx += 1

    return paths


# ------------------------------------------------------------------ Annotations
def circle_annotation_path(box: Tuple[float, float, float, float], overshoot: float = 1.15) -> Path:
    """Hand-drawn looping circle/oval around a target bounding box."""
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    rx = (x1 - x0) / 2.0 + 8.0
    ry = (y1 - y0) / 2.0 + 6.0

    p = Path()
    # Spiral oval that loops around ~1.15 times with hand-drawn wobble
    pts = 28
    for i in range(int(pts * overshoot)):
        angle = (i / float(pts)) * 2.0 * math.pi
        rad_x = rx + math.sin(angle * 2) * 1.5
        rad_y = ry + math.cos(angle * 3) * 1.2
        px = cx + rad_x * math.cos(angle)
        py = cy + rad_y * math.sin(angle)
        if i == 0:
            p.move_to(px, py)
        else:
            p.line_to(px, py)
    p.end()
    return p


def underline_annotation_path(xy: Point, length: float, style: str = "wave") -> Path:
    """Hand-drawn underline (wave, double, or sketchy line)."""
    p = Path()
    x, y = xy
    if style == "wave":
        waves = max(2, int(length // 16))
        p.move_to(x, y)
        for i in range(waves):
            x_mid = x + (i + 0.5) * (length / waves)
            x_end = x + (i + 1) * (length / waves)
            p.quad_to(x_mid, y + 4.0, x_end, y)
    elif style == "double":
        p.move_to(x, y).line_to(x + length, y + 1)
        p.move_to(x + 4, y + 4).line_to(x + length - 2, y + 5)
    else:
        p.move_to(x, y).line_to(x + length, y + 1.5)
    p.end()
    return p


def bracket_annotation_path(x: float, y0: float, y1: float, side: str = "left", tip_offset: float = 10.0) -> Path:
    """Hand-drawn curly bracket { or }."""
    p = Path()
    ym = (y0 + y1) / 2.0
    sgn = 1.0 if side == "left" else -1.0
    dx = tip_offset * sgn

    p.move_to(x + dx, y0)
    p.cubic_to(x, y0 + 10, x, ym - 10, x - dx, ym)
    p.cubic_to(x, ym + 10, x, y1 - 10, x + dx, y1)
    p.end()
    return p


def curved_arrow_path(p0: Point, p1: Point, bend: float = 0.25) -> Path:
    """Hand-drawn arc arrow with sketchy arrowhead."""
    d = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
    mx, my = (p0[0] + p1[0]) / 2.0, (p0[1] + p1[1]) / 2.0
    nx, ny = -(p1[1] - p0[1]) / max(1e-4, d), (p1[0] - p0[0]) / max(1e-4, d)
    ctrl = (mx + nx * d * bend, my + ny * d * bend)

    p = Path()
    p.move_to(p0[0], p0[1]).quad_to(ctrl[0], ctrl[1], p1[0], p1[1])

    # Arrowhead at p1
    angle = math.atan2(p1[1] - ctrl[1], p1[0] - ctrl[0])
    a_len = max(8.0, min(16.0, d * 0.15))
    h1 = (p1[0] - a_len * math.cos(angle - 0.45), p1[1] - a_len * math.sin(angle - 0.45))
    h2 = (p1[0] - a_len * math.cos(angle + 0.45), p1[1] - a_len * math.sin(angle + 0.45))

    p.move_to(h1[0], h1[1]).line_to(p1[0], p1[1]).line_to(h2[0], h2[1])
    p.end()
    return p


# ------------------------------------------------------------------ UI Mockups & Code Block
def get_browser_mockup_paths(box: Tuple[float, float, float, float], url: str = "https://app.dev") -> Tuple[List[Path], List[Tuple[Point, str]]]:
    """Generates hand-drawn browser window with address bar and buttons."""
    x, y, w, h = box
    paths: List[Path] = []
    text_labels: List[Tuple[Point, str]] = []

    # Window border & address header
    p_win = Path()
    p_win.move_to(x, y).line_to(x + w, y).line_to(x + w, y + h).line_to(x, y + h).close()
    p_win.move_to(x, y + 26).line_to(x + w, y + 26)
    # Three dots
    for q in range(3):
        cx, cy = x + 12 + q * 10, y + 13
        p_win.move_to(cx + 2.5, cy).arc_to(2.5, 2.5, 0, False, True, cx - 2.5, cy).arc_to(2.5, 2.5, 0, False, True, cx + 2.5, cy).close()
    # URL pill
    url_x = x + 48
    url_w = max(60.0, w - 80)
    p_win.move_to(url_x + 4, y + 6).line_to(url_x + url_w - 4, y + 6).arc_to(4, 4, 0, False, True, url_x + url_w, y + 10).line_to(url_x + url_w, y + 18).arc_to(4, 4, 0, False, True, url_x + url_w - 4, y + 22).line_to(url_x + 4, y + 22).arc_to(4, 4, 0, False, True, url_x, y + 18).line_to(url_x, y + 10).arc_to(4, 4, 0, False, True, url_x + 4, y + 6).close()
    paths.append(p_win)

    text_labels.append(((url_x + 10, y + 14), url))
    return paths, text_labels


def get_terminal_mockup_paths(box: Tuple[float, float, float, float]) -> List[Path]:
    """Generates hand-drawn terminal console window."""
    x, y, w, h = box
    p = Path()
    p.move_to(x, y).line_to(x + w, y).line_to(x + w, y + h).line_to(x, y + h).close()
    p.move_to(x, y + 22).line_to(x + w, y + 22)
    # Prompt prompt symbol $
    p.move_to(x + 10, y + 36).line_to(x + 16, y + 42).line_to(x + 10, y + 48)
    p.end()
    return [p]


def get_phone_mockup_paths(box: Tuple[float, float, float, float]) -> List[Path]:
    """Generates hand-drawn smartphone mockup with rounded bezel."""
    x, y, w, h = box
    p = Path()
    r = 16.0
    p.move_to(x + r, y).line_to(x + w - r, y).arc_to(r, r, 0, False, True, x + w, y + r).line_to(x + w, y + h - r).arc_to(r, r, 0, False, True, x + w - r, y + h).line_to(x + r, y + h).arc_to(r, r, 0, False, True, x, y + h - r).line_to(x, y + r).arc_to(r, r, 0, False, True, x + r, y).close()
    # Speaker notch & home bar
    p.move_to(x + w / 2.0 - 16, y + 10).line_to(x + w / 2.0 + 16, y + 10)
    p.move_to(x + w / 2.0 - 20, y + h - 12).line_to(x + w / 2.0 + 20, y + h - 12)
    p.end()
    return [p]


# ------------------------------------------------------------------ Paper & Backgrounds
def render_paper_background(
    img: Image.Image,
    style: str = "dark",
    s_factor: int = 1
) -> Image.Image:
    """Applies stylized paper backgrounds (blueprint, notebook, chalkboard, sepia, grid)."""
    w, h = img.size
    draw = ImageDraw.Draw(img)

    if style == "notebook":
        # White ground, blue horizontal ruled lines, pink left margin
        img.paste((252, 252, 250), [0, 0, w, h])
        margin_x = int(60 * s_factor)
        draw.line([(margin_x, 0), (margin_x, h)], fill=(245, 160, 160), width=max(1, int(1.5 * s_factor)))
        line_spacing = int(24 * s_factor)
        for y in range(int(36 * s_factor), h, line_spacing):
            draw.line([(0, y), (w, y)], fill=(200, 220, 245), width=1)

    elif style == "blueprint":
        # Deep cyan/blue with light blueprint grid
        img.paste((12, 45, 95), [0, 0, w, h])
        grid = int(24 * s_factor)
        for x in range(0, w, grid):
            draw.line([(x, 0), (x, h)], fill=(25, 75, 140), width=1)
        for y in range(0, h, grid):
            draw.line([(0, y), (w, y)], fill=(25, 75, 140), width=1)

    elif style == "chalkboard":
        # Dusty dark green/grey
        img.paste((24, 34, 28), [0, 0, w, h])

    elif style == "sepia":
        # Warm aged parchment
        img.paste((245, 238, 220), [0, 0, w, h])

    elif style == "grid":
        # Subtle light engineering grid
        grid = int(20 * s_factor)
        for x in range(0, w, grid):
            draw.line([(x, 0), (x, h)], fill=(40, 40, 45), width=1)
        for y in range(0, h, grid):
            draw.line([(0, y), (w, y)], fill=(40, 40, 45), width=1)

    return img
