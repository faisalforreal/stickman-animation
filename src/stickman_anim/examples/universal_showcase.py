"""Showcase of Universal Generator Engine features:
Icons, SVG import, LaTeX math, Mermaid diagrams, xkcd charts, and hand-drawn annotations.
"""
from stickman_anim import *

N = 40

def render(f):
    c = Frame(f)
    c.background("notebook")

    # Title
    c.text((320, 25), "Universal Drawing Engine", font(18), WHITE, "mm")

    # Icons
    prog_icon = clamp((f + 1) / 15.0)
    c.icon("github", (80, 80), size=44, col=CYAN, draw_on=prog_icon, pen=True)
    c.icon("bot", (160, 80), size=44, col=GREEN, draw_on=clamp((f - 5) / 15.0), pen=True)

    # Annotations
    c.annotate_circle((55, 55, 105, 105), col=CYAN, progress=clamp((f - 10) / 10.0))
    c.annotate_underline((230, 80), 80, style="wave", col=GREEN, progress=clamp((f - 12) / 10.0))
    c.text((270, 68), "Auto-Icons", font(12), WHITE, "mm")

    # LaTeX Math
    c.latex(r"E = mc^2", (360, 75), size=24, col=WHITE, draw_on=clamp((f - 8) / 15.0), pen=True)

    # UI Browser Mockup
    c.mockup_browser((50, 130, 240, 100), url="https://antigravity.dev", col=WHITE, progress=clamp((f - 5) / 15.0))

    # Mermaid Diagram
    mermaid_code = """graph LR
    Push --> Test
    Test --> Deploy"""
    c.mermaid(mermaid_code, (320, 130, 260, 100), col=WHITE, draw_on=clamp((f - 10) / 18.0), active_node="Test")

    # xkcd Chart
    chart_data = [("Mon", 20), ("Tue", 45), ("Wed", 85)]
    c.chart_bar((80, 260, 200, 70), chart_data, title="Deploy Velocity", col=CYAN, progress=clamp((f - 15) / 15.0))

    # Robot & Human Characters
    c.robot(360, 330, eye=CYAN, hr=(400, 270))
    c.human(480, 330, thumbs_up=True)

    return c.image()

if __name__ == "__main__":
    main(render, N, "universal_showcase", [5, 18, 38])
