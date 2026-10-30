"""Phase H Animated SVG and Social Distribution Demo.

Demonstrates:
- Exporting vector paths to a resolution-independent Animated SVG.
- Intelligent auto-thumbnail generation with engagement scoring.
"""
from stickman_anim import *
from stickman_anim.paths import Path
from stickman_anim.icons import get_icon_paths
from stickman_anim.exporters import export_animated_svg, generate_thumbnail


def main_phase_h():
    # 1. Assemble vector paths for animated SVG
    paths = []
    # Tech icons
    paths.extend(get_icon_paths("rocket", (120, 160, 60, 60)))
    paths.extend(get_icon_paths("bot", (260, 160, 60, 60)))
    paths.extend(get_icon_paths("sparkles", (400, 160, 60, 60)))

    # Frame and underline paths
    box_p = Path()
    box_p.move_to(60, 80).line_to(580, 80).line_to(580, 280).line_to(60, 280).close()
    paths.append(box_p)

    svg_out = "docs/gallery/animated_vector.svg"
    export_animated_svg(paths, svg_out, width=640, height=360, duration_sec=3.0)
    print(f"Generated resolution-independent Animated SVG: {svg_out}")

    # 2. Render sample frames to showcase auto-thumbnail generator
    frames = []
    for f in range(20):
        c = Frame(f)
        c.background("dark")
        c.floor(310)
        c.character(320, 310, kind="robot", action="celebrate", t=float(f), accessories=["crown"])
        if f > 10:
            c.confetti((320, 180), t=float(f - 10) * 0.1, count=25)
            c.emote((320, 210), kind="heart")
        frames.append(c.image())

    thumb_out = "docs/gallery/social_showcase_thumb.png"
    generate_thumbnail(frames, output_path=thumb_out, title_badge="Phase H: Unlimited Engine")
    print(f"Generated engagement-scored thumbnail: {thumb_out}")


if __name__ == "__main__":
    main_phase_h()
