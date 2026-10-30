"""Phase G & F Declarative Storyboard, Self-QA Linter, and Caption Upgrades Demo.

Demonstrates:
- Pure declarative JSON/dict storyboard specification.
- Pre-render Self-QA bounds checking.
- Automated generation of video with characters, icons, text, and styled captions.
"""
import os
import shutil
import subprocess
from stickman_anim import *
from stickman_anim.storyboard import render_storyboard


STORYBOARD = {
    "title": "Agent Showcase",
    "aspect": "16:9",
    "ms": 120,
    "style": "hormozi-bold",
    "scenes": [
        {
            "name": "introduction",
            "frames": 24,
            "background": "dark",
            "floor_y": 310.0,
            "elements": [
                {"type": "character", "cx": 200, "floor_y": 310, "kind": "human", "action": "point", "accessories": ["glasses"]},
                {"type": "icon", "name": "rocket", "pos": [440, 140], "size": 44, "col": [80, 220, 255]},
                {"type": "text", "pos": [320, 40], "text": "Declarative Storyboard Engine"}
            ]
        },
        {
            "name": "celebration",
            "frames": 24,
            "background": "notebook",
            "floor_y": 310.0,
            "transition": "wipe",
            "elements": [
                {"type": "character", "cx": 320, "floor_y": 310, "kind": "robot", "action": "celebrate", "accessories": ["crown"]},
                {"type": "particles", "particle_type": "confetti", "origin": [320, 180], "count": 25},
                {"type": "speech_bubble", "speaker_pos": [320, 210], "text": "100% Agent Generated!"},
                {"type": "text", "pos": [320, 40], "text": "Unlimited Hand-Drawn Magic"}
            ]
        }
    ]
}


def main_storyboard():
    out_mp4 = "docs/gallery/declarative_storyboard_demo.mp4"
    res = render_storyboard(STORYBOARD, output_path=out_mp4, lint=True)
    print(f"Rendered storyboard to {res}")

    if shutil.which("ffmpeg"):
        gif_out = "docs/gallery/declarative_storyboard_demo.gif"
        subprocess.run([
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", res, "-vf", "fps=10,scale=640:-1:flags=lanczos",
            gif_out
        ], check=True)
        print(f"Generated gallery GIF preview: {gif_out}")


if __name__ == "__main__":
    main_storyboard()
