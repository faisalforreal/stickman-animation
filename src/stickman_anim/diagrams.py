"""Diagram and chart generators for stickman_anim.

Provides:
- Mermaid diagram parser (Flowcharts & Sequence diagrams) with auto-DAG layout.
- xkcd-style hand-drawn charts: Bar, Line, Pie, Scatter, and Sankey.
"""

import math
import re
from typing import List, Tuple, Dict, Any, Optional
from .paths import Path, Point, LineSegment, QuadSegment
from .generators import curved_arrow_path, circle_annotation_path


# ------------------------------------------------------------------ Mermaid & DAG Auto-Layout
class DiagramNode:
    def __init__(self, node_id: str, label: str, shape: str = "rect"):
        self.id = node_id
        self.label = label
        self.shape = shape  # 'rect', 'diamond', 'round', 'cylinder'
        self.x = 0.0
        self.y = 0.0
        self.w = 90.0
        self.h = 36.0
        self.layer = 0


class DiagramEdge:
    def __init__(self, u: str, v: str, label: str = ""):
        self.u = u
        self.v = v
        self.label = label


def parse_mermaid(text: str) -> Tuple[Dict[str, DiagramNode], List[DiagramEdge], str]:
    """Parse basic Mermaid flowchart (graph TD/LR) or sequence diagram."""
    lines = [ln.strip() for ln in text.strip().split("\n") if ln.strip() and not ln.strip().startswith("%%")]
    diagram_type = "flowchart_td"
    if lines and ("graph lr" in lines[0].lower() or "flowchart lr" in lines[0].lower()):
        diagram_type = "flowchart_lr"
    elif lines and "sequencediagram" in lines[0].lower():
        diagram_type = "sequence"

    nodes: Dict[str, DiagramNode] = {}
    edges: List[DiagramEdge] = []

    node_pattern = re.compile(r"([a-zA-Z0-9_]+)\s*(\[\[?|\{\{?|\(\(?|\[\()([^\]\}\)]+)(\]\]?|\}\}?|\)\)?|\)\])")
    edge_pattern = re.compile(r"([a-zA-Z0-9_]+)\s*(?:-->|->)\s*(?:\|([^|]+)\|)?\s*([a-zA-Z0-9_]+)")

    for line in lines[1:] if len(lines) > 1 else lines:
        cleaned_line = line
        # 1. Extract explicit node declarations and simplify line to identifiers
        for n_match in node_pattern.finditer(line):
            nid, open_br, label, close_br = n_match.group(1), n_match.group(2), n_match.group(3), n_match.group(4)
            shape = "rect"
            if "{" in open_br:
                shape = "diamond"
            elif "((" in open_br:
                shape = "round"
            elif "[(" in open_br:
                shape = "cylinder"
            node = DiagramNode(nid, label.strip(), shape)
            node.w = max(80.0, len(label.strip()) * 9.0 + 24.0)
            nodes[nid] = node
            cleaned_line = cleaned_line.replace(n_match.group(0), nid)

        # 2. Extract edge connections
        edge_match = edge_pattern.search(cleaned_line)
        if edge_match:
            u, lbl, v = edge_match.group(1), edge_match.group(2) or "", edge_match.group(3)
            if u not in nodes:
                nodes[u] = DiagramNode(u, u)
            if v not in nodes:
                nodes[v] = DiagramNode(v, v)
            edges.append(DiagramEdge(u, v, lbl.strip()))

    return nodes, edges, diagram_type


def layout_flowchart(
    nodes: Dict[str, DiagramNode],
    edges: List[DiagramEdge],
    box: Tuple[float, float, float, float],
    is_lr: bool = False
) -> None:
    """Layered topological Sugiyama layout inside target bounding box."""
    if not nodes:
        return

    # Topological layering via Longest Path from roots
    in_degree = {nid: 0 for nid in nodes}
    adj: Dict[str, List[str]] = {nid: [] for nid in nodes}
    for e in edges:
        if e.u in nodes and e.v in nodes:
            adj[e.u].append(e.v)
            in_degree[e.v] += 1

    layers: Dict[int, List[str]] = {}
    visited = set()

    def assign_layer(nid, l):
        nodes[nid].layer = max(nodes[nid].layer, l)
        for nxt in adj[nid]:
            assign_layer(nxt, l + 1)

    roots = [nid for nid, deg in in_degree.items() if deg == 0] or list(nodes.keys())[:1]
    for r in roots:
        assign_layer(r, 0)

    for nid, node in nodes.items():
        layers.setdefault(node.layer, []).append(nid)

    num_layers = max(layers.keys()) + 1 if layers else 1
    bx, by, bw, bh = box

    if not is_lr:  # Top-Down (TD)
        layer_h = bh / max(1, num_layers)
        for l, nids in layers.items():
            slot_w = bw / max(1, len(nids))
            for idx, nid in enumerate(nids):
                nodes[nid].x = bx + (idx + 0.5) * slot_w
                nodes[nid].y = by + (l + 0.5) * layer_h
    else:  # Left-Right (LR)
        layer_w = bw / max(1, num_layers)
        for l, nids in layers.items():
            slot_h = bh / max(1, len(nids))
            for idx, nid in enumerate(nids):
                nodes[nid].x = bx + (l + 0.5) * layer_w
                nodes[nid].y = by + (idx + 0.5) * slot_h


def render_diagram_paths(
    mermaid_code: str,
    box: Tuple[float, float, float, float]
) -> Tuple[List[Path], List[Tuple[Point, str]], List[Tuple[Point, str]]]:
    """Compiles Mermaid diagram into paths and label positions."""
    nodes, edges, dtype = parse_mermaid(mermaid_code)
    is_lr = (dtype == "flowchart_lr")
    layout_flowchart(nodes, edges, box, is_lr=is_lr)

    paths: List[Path] = []
    node_labels: List[Tuple[Point, str]] = []
    edge_labels: List[Tuple[Point, str]] = []

    # Render node shapes
    for node in nodes.values():
        p = Path()
        x, y, w, h = node.x - node.w / 2.0, node.y - node.h / 2.0, node.w, node.h
        if node.shape == "rect":
            p.move_to(x, y).line_to(x + w, y).line_to(x + w, y + h).line_to(x, y + h).close()
        elif node.shape == "diamond":
            cx, cy = node.x, node.y
            p.move_to(cx, y).line_to(x + w, cy).line_to(cx, y + h).line_to(x, cy).close()
        elif node.shape == "round":
            r = max(w, h) / 2.0
            cx, cy = node.x, node.y
            p.move_to(cx + r, cy).arc_to(r, r, 0, False, True, cx - r, cy).arc_to(r, r, 0, False, True, cx + r, cy).close()
        elif node.shape == "cylinder":
            # Database cylinder
            p.move_to(x, y + 8).line_to(x, y + h - 8).arc_to(w / 2, 8, 0, False, True, x + w, y + h - 8).line_to(x + w, y + 8)
            p.arc_to(w / 2, 8, 0, False, True, x, y + 8).arc_to(w / 2, 8, 0, False, True, x + w, y + 8)
            p.end()
        paths.append(p)
        node_labels.append(((node.x, node.y), node.label))

    # Render edges
    for e in edges:
        u_node, v_node = nodes.get(e.u), nodes.get(e.v)
        if not u_node or not v_node:
            continue
        p0 = (u_node.x, u_node.y + u_node.h / 2.0 if not is_lr else u_node.x + u_node.w / 2.0, u_node.y)
        p1 = (v_node.x, v_node.y - v_node.h / 2.0 if not is_lr else v_node.x - v_node.w / 2.0, v_node.y)
        
        # Start and end points
        start_pt = (u_node.x, u_node.y + u_node.h / 2.0) if not is_lr else (u_node.x + u_node.w / 2.0, u_node.y)
        end_pt = (v_node.x, v_node.y - v_node.h / 2.0) if not is_lr else (v_node.x - v_node.w / 2.0, v_node.y)

        arrow_p = curved_arrow_path(start_pt, end_pt, bend=0.1)
        paths.append(arrow_p)

        if e.label:
            mid = ((start_pt[0] + end_pt[0]) / 2.0 + 8.0, (start_pt[1] + end_pt[1]) / 2.0)
            edge_labels.append((mid, e.label))

    return paths, node_labels, edge_labels


# ------------------------------------------------------------------ xkcd-Style Charts
def chart_bar_paths(
    box: Tuple[float, float, float, float],
    data: List[Tuple[str, float]],
    title: str = "",
    progress: float = 1.0
) -> Tuple[List[Path], List[Tuple[Point, str]]]:
    """Hand-drawn bar chart with animated bar height progress."""
    x, y, w, h = box
    paths: List[Path] = []
    labels: List[Tuple[Point, str]] = []

    # Axes
    p_axes = Path()
    p_axes.move_to(x, y).line_to(x, y + h).line_to(x + w, y + h).end()
    paths.append(p_axes)

    if title:
        labels.append(((x + w / 2.0, y - 10), title))

    if not data:
        return paths, labels

    max_val = max(1e-4, max(v for _, v in data))
    bar_slot = (w - 20) / len(data)
    bar_w = bar_slot * 0.65

    for i, (label, val) in enumerate(data):
        bar_h = (val / max_val) * (h - 25) * max(0.0, min(1.0, progress))
        bx = x + 16 + i * bar_slot
        by = y + h - bar_h

        p_bar = Path()
        p_bar.move_to(bx, y + h).line_to(bx, by).line_to(bx + bar_w, by).line_to(bx + bar_w, y + h).close()
        paths.append(p_bar)

        labels.append(((bx + bar_w / 2.0, y + h + 12), label))
        if progress >= 0.8:
            labels.append(((bx + bar_w / 2.0, by - 8), f"{val:g}"))

    return paths, labels


def chart_line_paths(
    box: Tuple[float, float, float, float],
    series: List[float],
    labels_x: Optional[List[str]] = None,
    title: str = "",
    progress: float = 1.0
) -> Tuple[List[Path], List[Tuple[Point, str]]]:
    """Hand-drawn line chart with draw-on progression."""
    x, y, w, h = box
    paths: List[Path] = []
    labels: List[Tuple[Point, str]] = []

    # Axes
    p_axes = Path()
    p_axes.move_to(x, y).line_to(x, y + h).line_to(x + w, y + h).end()
    paths.append(p_axes)

    if title:
        labels.append(((x + w / 2.0, y - 10), title))

    if len(series) < 2:
        return paths, labels

    max_val = max(1e-4, max(series))
    min_val = min(0.0, min(series))
    val_range = max(1e-4, max_val - min_val)

    pts = []
    step_x = (w - 20) / (len(series) - 1)
    for i, val in enumerate(series):
        px = x + 10 + i * step_x
        py = y + h - ((val - min_val) / val_range) * (h - 25)
        pts.append((px, py))

    p_line = Path()
    p_line.move_to(pts[0][0], pts[0][1])
    for pt in pts[1:]:
        p_line.line_to(pt[0], pt[1])
    p_line.end()

    # Slice line by progress
    if progress < 1.0:
        sliced_polys = p_line.slice(progress)
        if sliced_polys:
            p_sliced = Path()
            for poly in sliced_polys:
                if not poly:
                    continue
                p_sliced.move_to(poly[0][0], poly[0][1])
                for pt in poly[1:]:
                    p_sliced.line_to(pt[0], pt[1])
                p_sliced.end()
            paths.append(p_sliced)
    else:
        paths.append(p_line)

    # Dots at vertices
    visible_count = int(len(pts) * progress)
    for i in range(visible_count):
        pt = pts[i]
        p_dot = Path()
        p_dot.move_to(pt[0] + 3, pt[1]).arc_to(3, 3, 0, False, True, pt[0] - 3, pt[1]).arc_to(3, 3, 0, False, True, pt[0] + 3, pt[1]).close()
        paths.append(p_dot)
        if labels_x and i < len(labels_x):
            labels.append(((pt[0], y + h + 12), labels_x[i]))

    return paths, labels


def chart_pie_paths(
    center: Point,
    radius: float,
    data: List[Tuple[str, float]],
    progress: float = 1.0
) -> Tuple[List[Path], List[Tuple[Point, str]]]:
    """Hand-drawn pie chart with wedge reveals."""
    cx, cy = center
    paths: List[Path] = []
    labels: List[Tuple[Point, str]] = []

    total = sum(v for _, v in data)
    if total <= 0:
        return paths, labels

    curr_ang = -math.pi / 2.0
    for label, val in data:
        span = (val / total) * 2.0 * math.pi * max(0.0, min(1.0, progress))
        if span <= 1e-3:
            continue
        p = Path()
        p.move_to(cx, cy)
        p1 = (cx + radius * math.cos(curr_ang), cy + radius * math.sin(curr_ang))
        p.line_to(p1[0], p1[1])
        # Arc to end of wedge
        p2 = (cx + radius * math.cos(curr_ang + span), cy + radius * math.sin(curr_ang + span))
        large_arc = span > math.pi
        p.arc_to(radius, radius, 0, large_arc, True, p2[0], p2[1])
        p.close()
        paths.append(p)

        # Label position at mid-angle outside pie
        mid_ang = curr_ang + span / 2.0
        lx = cx + (radius + 18) * math.cos(mid_ang)
        ly = cy + (radius + 18) * math.sin(mid_ang)
        labels.append(((lx, ly), f"{label} ({(val/total)*100:.0f}%)"))

        curr_ang += span

    return paths, labels
