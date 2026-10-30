"""Phase D Multi-Scene Timeline, Transitions, and Caching Demo.

Demonstrates:
- Multi-scene timeline sequencing (Scene 1 -> Wipe -> Scene 2).
- Automatic aspect ratio presets and safe caption zones.
- Scene hashing and cache reuse.
"""
from stickman_anim import *
from stickman_anim.timeline import Timeline, Scene


def render_scene_1(f):
    c = Frame(f)
    t = float(f)
    c.background("dark")
    c.floor(310)
    c.character(200, 310, kind="human", action="fail", t=t)
    c.emote((200, 215), kind="?")
    c.speech_bubble((200, 200), "Too many bugs!", thought=False, progress=1.0)
    c.text((320, 32), "Scene 1: The Problem", font(18), WHITE, "mm")
    return c.image()


def render_scene_2(f):
    c = Frame(f)
    t = float(f)
    c.background("notebook")
    c.floor(310)
    c.character(320, 310, kind="robot", action="celebrate", t=t, accessories=["crown"])
    c.confetti((320, 200), t=t * 0.1, count=20)
    c.speech_bubble((320, 200), "AI Agents to the rescue!", thought=False, progress=1.0)
    c.text((320, 32), "Scene 2: The Solution", font(18), WHITE, "mm")
    return c.image()


def main_timeline():
    tl = Timeline(aspect="16:9", ms=120)
    tl.add_scene(Scene(
        name="problem",
        render_fn=render_scene_1,
        frames=18,
        transition_to_next="wipe",
        transition_frames=6
    ))
    tl.add_scene(Scene(
        name="solution",
        render_fn=render_scene_2,
        frames=18,
        transition_to_next="cut"
    ))

    out_path = "docs/gallery/timeline_demo.mp4"
    res = tl.render_all(out_path)
    print(f"Rendered multi-scene timeline to {res}")

    # Also convert a preview to GIF for gallery viewing
    import subprocess
    import shutil
    if shutil.which("ffmpeg"):
        gif_out = "docs/gallery/timeline_demo.gif"
        subprocess.run([
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", res, "-vf", "fps=10,scale=640:-1:flags=lanczos",
            gif_out
        ], check=True)
        print(f"Generated gallery GIF preview: {gif_out}")


if __name__ == "__main__":
    main_timeline()
