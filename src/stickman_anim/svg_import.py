"""Pure-Python SVG parser and converter into stickman_anim Paths.

Converts SVG files or strings into lists of Path objects,
ready for sketchy hand-drawn rendering and draw-on animations.
"""

import math
import re
import xml.etree.ElementTree as ET
from typing import List, Tuple, Optional, Dict, Any
from .paths import Path, Point


# Tokenizer regex for SVG path 'd' attribute
_PATH_TOKEN_RE = re.compile(r"([MmLlHhVvCcSsQqTtAaZz])|([-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?)")


def _tokenize_d(d_str: str) -> List[str]:
    return [match.group(0) for match in _PATH_TOKEN_RE.finditer(d_str)]


class Transform:
    """2D Affine Transformation Matrix."""
    def __init__(self, a=1.0, b=0.0, c=0.0, d=1.0, e=0.0, f=0.0):
        self.a, self.b, self.c, self.d, self.e, self.f = a, b, c, d, e, f

    def apply(self, pt: Point) -> Point:
        return (
            self.a * pt[0] + self.c * pt[1] + self.e,
            self.b * pt[0] + self.d * pt[1] + self.f,
        )

    def multiply(self, other: "Transform") -> "Transform":
        return Transform(
            self.a * other.a + self.c * other.b,
            self.b * other.a + self.d * other.b,
            self.a * other.c + self.c * other.d,
            self.b * other.c + self.d * other.d,
            self.a * other.e + self.c * other.f + self.e,
            self.b * other.e + self.d * other.f + self.f,
        )


def parse_transform(t_str: str) -> Transform:
    """Parse SVG transform attribute (translate, scale, rotate, matrix)."""
    t = Transform()
    if not t_str:
        return t

    matches = re.findall(r"([a-z]+)\s*\(([^)]+)\)", t_str, re.IGNORECASE)
    for name, args_str in matches:
        args = [float(x.strip()) for x in re.split(r"[\s,]+", args_str.strip()) if x.strip()]
        name = name.lower()
        if name == "translate":
            tx = args[0]
            ty = args[1] if len(args) > 1 else 0.0
            t = t.multiply(Transform(1, 0, 0, 1, tx, ty))
        elif name == "scale":
            sx = args[0]
            sy = args[1] if len(args) > 1 else sx
            t = t.multiply(Transform(sx, 0, 0, sy, 0, 0))
        elif name == "rotate":
            rad = math.radians(args[0])
            cos_a, sin_a = math.cos(rad), math.sin(rad)
            if len(args) == 3:
                cx, cy = args[1], args[2]
                t = t.multiply(Transform(1, 0, 0, 1, cx, cy))
                t = t.multiply(Transform(cos_a, sin_a, -sin_a, cos_a, 0, 0))
                t = t.multiply(Transform(1, 0, 0, 1, -cx, -cy))
            else:
                t = t.multiply(Transform(cos_a, sin_a, -sin_a, cos_a, 0, 0))
        elif name == "matrix" and len(args) == 6:
            t = t.multiply(Transform(*args))
    return t


def parse_svg_path_d(d_str: str, transform: Optional[Transform] = None) -> List[Path]:
    """Parse an SVG path 'd' string into a list of Path objects."""
    tokens = _tokenize_d(d_str)
    if not tokens:
        return []

    paths: List[Path] = []
    current_path: Optional[Path] = None
    i = 0
    cmd = ""
    curr_x, curr_y = 0.0, 0.0
    start_x, start_y = 0.0, 0.0
    last_cp: Optional[Point] = None

    def transform_pt(x: float, y: float) -> Point:
        return transform.apply((x, y)) if transform else (x, y)

    while i < len(tokens):
        token = tokens[i]
        if token in "MmLlHhVvCcSsQqTtAaZz":
            cmd = token
            i += 1
        # If consecutive numbers without command, continue with previous command
        # (special rule: subsequent coordinates after M/m are treated as L/l)
        if cmd == "M" or cmd == "m":
            if i + 1 >= len(tokens):
                break
            x, y = float(tokens[i]), float(tokens[i+1])
            i += 2
            if cmd == "m":
                x += curr_x
                y += curr_y
            curr_x, curr_y = x, y
            start_x, start_y = x, y
            last_cp = None

            current_path = Path()
            pt = transform_pt(x, y)
            current_path.move_to(pt[0], pt[1])
            paths.append(current_path)
            cmd = "L" if cmd == "M" else "l"

        elif cmd == "L" or cmd == "l":
            if i + 1 >= len(tokens):
                break
            x, y = float(tokens[i]), float(tokens[i+1])
            i += 2
            if cmd == "l":
                x += curr_x
                y += curr_y
            curr_x, curr_y = x, y
            last_cp = None
            if current_path:
                pt = transform_pt(x, y)
                current_path.line_to(pt[0], pt[1])

        elif cmd == "H" or cmd == "h":
            if i >= len(tokens):
                break
            x = float(tokens[i])
            i += 1
            if cmd == "h":
                x += curr_x
            curr_x = x
            last_cp = None
            if current_path:
                pt = transform_pt(curr_x, curr_y)
                current_path.line_to(pt[0], pt[1])

        elif cmd == "V" or cmd == "v":
            if i >= len(tokens):
                break
            y = float(tokens[i])
            i += 1
            if cmd == "v":
                y += curr_y
            curr_y = y
            last_cp = None
            if current_path:
                pt = transform_pt(curr_x, curr_y)
                current_path.line_to(pt[0], pt[1])

        elif cmd == "C" or cmd == "c":
            if i + 5 >= len(tokens):
                break
            c1x, c1y = float(tokens[i]), float(tokens[i+1])
            c2x, c2y = float(tokens[i+2]), float(tokens[i+3])
            x, y = float(tokens[i+4]), float(tokens[i+5])
            i += 6
            if cmd == "c":
                c1x += curr_x
                c1y += curr_y
                c2x += curr_x
                c2y += curr_y
                x += curr_x
                y += curr_y
            last_cp = (c2x, c2y)
            curr_x, curr_y = x, y
            if current_path:
                p1 = transform_pt(c1x, c1y)
                p2 = transform_pt(c2x, c2y)
                p3 = transform_pt(x, y)
                current_path.cubic_to(p1[0], p1[1], p2[0], p2[1], p3[0], p3[1])

        elif cmd == "S" or cmd == "s":
            if i + 3 >= len(tokens):
                break
            c2x, c2y = float(tokens[i]), float(tokens[i+1])
            x, y = float(tokens[i+2]), float(tokens[i+3])
            i += 4
            if cmd == "s":
                c2x += curr_x
                c2y += curr_y
                x += curr_x
                y += curr_y
            # Smooth cubic: c1 is reflection of previous c2 about current point
            if last_cp:
                c1x = 2.0 * curr_x - last_cp[0]
                c1y = 2.0 * curr_y - last_cp[1]
            else:
                c1x, c1y = curr_x, curr_y
            last_cp = (c2x, c2y)
            curr_x, curr_y = x, y
            if current_path:
                p1 = transform_pt(c1x, c1y)
                p2 = transform_pt(c2x, c2y)
                p3 = transform_pt(x, y)
                current_path.cubic_to(p1[0], p1[1], p2[0], p2[1], p3[0], p3[1])

        elif cmd == "Q" or cmd == "q":
            if i + 3 >= len(tokens):
                break
            cx, cy = float(tokens[i]), float(tokens[i+1])
            x, y = float(tokens[i+2]), float(tokens[i+3])
            i += 4
            if cmd == "q":
                cx += curr_x
                cy += curr_y
                x += curr_x
                y += curr_y
            last_cp = (cx, cy)
            curr_x, curr_y = x, y
            if current_path:
                p1 = transform_pt(cx, cy)
                p2 = transform_pt(x, y)
                current_path.quad_to(p1[0], p1[1], p2[0], p2[1])

        elif cmd == "T" or cmd == "t":
            if i + 1 >= len(tokens):
                break
            x, y = float(tokens[i]), float(tokens[i+1])
            i += 2
            if cmd == "t":
                x += curr_x
                y += curr_y
            if last_cp:
                cx = 2.0 * curr_x - last_cp[0]
                cy = 2.0 * curr_y - last_cp[1]
            else:
                cx, cy = curr_x, curr_y
            last_cp = (cx, cy)
            curr_x, curr_y = x, y
            if current_path:
                p1 = transform_pt(cx, cy)
                p2 = transform_pt(x, y)
                current_path.quad_to(p1[0], p1[1], p2[0], p2[1])

        elif cmd == "A" or cmd == "a":
            if i + 6 >= len(tokens):
                break
            rx, ry = float(tokens[i]), float(tokens[i+1])
            angle = float(tokens[i+2])
            large_arc = bool(int(tokens[i+3]))
            sweep = bool(int(tokens[i+4]))
            x, y = float(tokens[i+5]), float(tokens[i+6])
            i += 7
            if cmd == "a":
                x += curr_x
                y += curr_y
            curr_x, curr_y = x, y
            last_cp = None
            if current_path:
                p_end = transform_pt(x, y)
                # Note: elliptical arc approximation
                current_path.arc_to(rx, ry, angle, large_arc, sweep, p_end[0], p_end[1])

        elif cmd == "Z" or cmd == "z":
            curr_x, curr_y = start_x, start_y
            last_cp = None
            if current_path:
                current_path.close()
            cmd = ""

        else:
            i += 1

    for p in paths:
        p.end()
    return paths


def parse_svg(svg_content_or_path: str, target_box: Optional[Tuple[float, float, float, float]] = None) -> List[Path]:
    """
    Parse an SVG file path or XML string into normalized Paths.
    target_box = (center_x, center_y, width, height) to auto-scale and center.
    """
    if svg_content_or_path.strip().startswith("<"):
        root = ET.fromstring(svg_content_or_path)
    else:
        tree = ET.parse(svg_content_or_path)
        root = tree.getroot()

    # Strip XML namespaces from tags
    for elem in root.iter():
        if "}" in elem.tag:
            elem.tag = elem.tag.split("}", 1)[1]

    # Extract viewBox or width/height
    view_box = root.attrib.get("viewBox")
    vb_x, vb_y, vb_w, vb_h = 0.0, 0.0, 100.0, 100.0
    if view_box:
        parts = [float(p.strip()) for p in re.split(r"[\s,]+", view_box.strip()) if p.strip()]
        if len(parts) == 4:
            vb_x, vb_y, vb_w, vb_h = parts
    else:
        def parse_len(val, default):
            if not val:
                return default
            num = re.sub(r"[^\d.]", "", val)
            return float(num) if num else default
        vb_w = parse_len(root.attrib.get("width"), 100.0)
        vb_h = parse_len(root.attrib.get("height"), 100.0)

    # Walk SVG tree and extract all shapes with inherited transforms
    all_paths: List[Path] = []

    def walk_element(elem: ET.Element, current_transform: Transform):
        local_t = parse_transform(elem.attrib.get("transform", ""))
        elem_transform = current_transform.multiply(local_t)

        tag = elem.tag.lower()
        if tag == "path":
            d = elem.attrib.get("d", "")
            if d:
                all_paths.extend(parse_svg_path_d(d, elem_transform))

        elif tag == "rect":
            x = float(elem.attrib.get("x", 0.0))
            y = float(elem.attrib.get("y", 0.0))
            w = float(elem.attrib.get("width", 0.0))
            h = float(elem.attrib.get("height", 0.0))
            rx = float(elem.attrib.get("rx", elem.attrib.get("ry", 0.0)))
            ry = float(elem.attrib.get("ry", rx))
            if w > 0 and h > 0:
                p = Path()
                if rx > 0 or ry > 0:
                    p.move_to(*elem_transform.apply((x + rx, y)))
                    p.line_to(*elem_transform.apply((x + w - rx, y)))
                    p.arc_to(rx, ry, 0, False, True, *elem_transform.apply((x + w, y + ry)))
                    p.line_to(*elem_transform.apply((x + w, y + h - ry)))
                    p.arc_to(rx, ry, 0, False, True, *elem_transform.apply((x + w - rx, y + h)))
                    p.line_to(*elem_transform.apply((x + rx, y + h)))
                    p.arc_to(rx, ry, 0, False, True, *elem_transform.apply((x, y + h - ry)))
                    p.line_to(*elem_transform.apply((x, y + ry)))
                    p.arc_to(rx, ry, 0, False, True, *elem_transform.apply((x + rx, y)))
                    p.close()
                else:
                    p.move_to(*elem_transform.apply((x, y)))
                    p.line_to(*elem_transform.apply((x + w, y)))
                    p.line_to(*elem_transform.apply((x + w, y + h)))
                    p.line_to(*elem_transform.apply((x, y + h)))
                    p.close()
                all_paths.append(p)

        elif tag == "circle":
            cx = float(elem.attrib.get("cx", 0.0))
            cy = float(elem.attrib.get("cy", 0.0))
            r = float(elem.attrib.get("r", 0.0))
            if r > 0:
                p = Path()
                p.move_to(*elem_transform.apply((cx + r, cy)))
                p.arc_to(r, r, 0, False, True, *elem_transform.apply((cx - r, cy)))
                p.arc_to(r, r, 0, False, True, *elem_transform.apply((cx + r, cy)))
                p.close()
                all_paths.append(p)

        elif tag == "ellipse":
            cx = float(elem.attrib.get("cx", 0.0))
            cy = float(elem.attrib.get("cy", 0.0))
            rx = float(elem.attrib.get("rx", 0.0))
            ry = float(elem.attrib.get("ry", 0.0))
            if rx > 0 and ry > 0:
                p = Path()
                p.move_to(*elem_transform.apply((cx + rx, cy)))
                p.arc_to(rx, ry, 0, False, True, *elem_transform.apply((cx - rx, cy)))
                p.arc_to(rx, ry, 0, False, True, *elem_transform.apply((cx + rx, cy)))
                p.close()
                all_paths.append(p)

        elif tag == "line":
            x1 = float(elem.attrib.get("x1", 0.0))
            y1 = float(elem.attrib.get("y1", 0.0))
            x2 = float(elem.attrib.get("x2", 0.0))
            y2 = float(elem.attrib.get("y2", 0.0))
            p = Path()
            p.move_to(*elem_transform.apply((x1, y1)))
            p.line_to(*elem_transform.apply((x2, y2)))
            all_paths.append(p)

        elif tag in ("polyline", "polygon"):
            raw_pts = elem.attrib.get("points", "")
            nums = [float(x.strip()) for x in re.split(r"[\s,]+", raw_pts.strip()) if x.strip()]
            if len(nums) >= 4:
                p = Path()
                p0 = elem_transform.apply((nums[0], nums[1]))
                p.move_to(p0[0], p0[1])
                for k in range(2, len(nums) - 1, 2):
                    pt = elem_transform.apply((nums[k], nums[k+1]))
                    p.line_to(pt[0], pt[1])
                if tag == "polygon":
                    p.close()
                all_paths.append(p)

        for child in elem:
            walk_element(child, elem_transform)

    walk_element(root, Transform())

    # Auto-fit into target_box (center_x, center_y, width, height)
    if target_box and all_paths:
        tcx, tcy, tw, th = target_box
        # Compute bounding box of extracted paths
        min_x = float("inf")
        min_y = float("inf")
        max_x = float("-inf")
        max_y = float("-inf")

        for p in all_paths:
            for poly in p.get_polylines():
                for pt in poly:
                    min_x = min(min_x, pt[0])
                    max_x = max(max_x, pt[0])
                    min_y = min(min_y, pt[1])
                    max_y = max(max_y, pt[1])

        if min_x < max_x and min_y < max_y:
            cur_w = max_x - min_x
            cur_h = max_y - min_y
            scale = min(tw / cur_w, th / cur_h)
            orig_cx = (min_x + max_x) / 2.0
            orig_cy = (min_y + max_y) / 2.0

            normalized_paths: List[Path] = []
            for p in all_paths:
                np = Path()
                for c in p.contours:
                    first = True
                    for seg in c:
                        pts = seg.sample()
                        for q in pts:
                            nx = tcx + (q[0] - orig_cx) * scale
                            ny = tcy + (q[1] - orig_cy) * scale
                            if first:
                                np.move_to(nx, ny)
                                first = False
                            else:
                                np.line_to(nx, ny)
                normalized_paths.append(np)
            return normalized_paths

    return all_paths
