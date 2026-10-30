import pytest
from stickman_anim import *
from stickman_anim.paths import Path, LineSegment, CubicSegment, apply_rough_bowing, generate_hatch_fill
from stickman_anim.svg_import import parse_svg, parse_svg_path_d
from stickman_anim.icons import get_icon_paths, load_icon_svg
from stickman_anim.diagrams import parse_mermaid, layout_flowchart, chart_bar_paths, chart_line_paths, chart_pie_paths
from stickman_anim.generators import parse_sketch_dsl, latex_to_math_paths, circle_annotation_path


def test_path_construction_and_slicing():
    p = Path()
    p.move_to(0, 0).line_to(100, 0).cubic_to(120, 20, 140, 20, 160, 0).close()
    assert len(p.contours) == 1
    total_len = p.total_length()
    assert total_len > 200

    # Slice at half progress
    half_polys = p.slice(0.5)
    assert len(half_polys) >= 1
    half_len = sum(sum(math.dist(poly[i], poly[i+1]) for i in range(len(poly)-1)) for poly in half_polys)
    assert abs(half_len - total_len * 0.5) < 5.0


def test_rough_bowing_and_hatch_fills():
    poly = [(0, 0), (100, 0), (100, 50), (0, 50), (0, 0)]
    rng = random.Random(42)
    strokes = apply_rough_bowing(poly, rng, double_stroke=True)
    assert len(strokes) == 2  # Double strokes

    hatch = generate_hatch_fill(poly, spacing=10.0, cross=False)
    assert len(hatch) >= 4
    crosshatch = generate_hatch_fill(poly, spacing=10.0, cross=True)
    assert len(crosshatch) > len(hatch)


def test_svg_import():
    sample_svg = """<svg viewBox="0 0 100 100">
        <rect x="10" y="10" width="80" height="80" rx="5" />
        <circle cx="50" cy="50" r="20" />
        <path d="M 20 20 L 80 80 M 80 20 L 20 80" />
    </svg>"""
    paths = parse_svg(sample_svg, target_box=(320, 180, 200, 200))
    assert len(paths) >= 3


def test_icon_pack():
    for name in ["github", "terminal", "cloud", "bot", "rocket", "server"]:
        svg = load_icon_svg(name)
        assert "<svg" in svg
        paths = get_icon_paths(name, (320, 180, 48, 48))
        assert len(paths) >= 1


def test_mermaid_and_charts():
    mermaid_code = """graph TD
    A[Build] --> B[Test]
    B --> C{Pass?}
    C -->|Yes| D[Deploy]"""
    nodes, edges, dtype = parse_mermaid(mermaid_code)
    assert len(nodes) == 4
    assert len(edges) == 3

    bar_paths, bar_labels = chart_bar_paths((50, 50, 200, 100), [("A", 10), ("B", 25)], progress=1.0)
    assert len(bar_paths) >= 3
    assert len(bar_labels) >= 2


def test_frame_universal_drawing_integration():
    c = Frame(0)
    c.background("notebook")

    # Icon
    c.icon("github", (80, 80), size=40, col=CYAN, draw_on=1.0)
    c.icon("bot", (160, 80), size=40, col=WHITE, draw_on=0.5, pen=True)

    # Annotations
    c.annotate_circle((60, 60, 100, 100), col=GREEN)
    c.annotate_underline((220, 80), 60, style="wave")
    c.arrow_curved((100, 120), (200, 180))

    # LaTeX
    c.latex(r"E = mc^2", (300, 80), size=24, col=WHITE)

    # UI Mockup
    c.mockup_browser((50, 140, 220, 120), url="https://antigravity.dev")

    # Mermaid
    c.mermaid("graph LR\nA[Push] --> B[Review]", (300, 140, 240, 100))

    # Chart
    c.chart_bar((50, 280, 160, 60), [("v1", 40), ("v2", 90)], title="Speed")

    img = c.image()
    assert img.size == (1280, 720)
