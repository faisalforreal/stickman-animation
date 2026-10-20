"""Command line: `stickman demo|render|flags|version`."""
import os
import runpy
import sys

USAGE = """usage: stickman <command> [flags]

commands:
  demo [name] [flags]      render a bundled example (pr_review, fewer_devs, ci_pipeline)
  render SCRIPT [flags]    run your own script with the format / theme flags applied
  flags                    list the format and theme flags
  version

flags (any order):
  gif | gif-hd | video-hd | video-4k      output format        (default gif-hd)
  bg-black (=fg-white) | bg-white (=fg-black)   colour theme   (default bg-black)

examples:
  stickman demo pr_review video-hd bg-white
  stickman render my_scene.py gif-hd
"""

FLAGS_HELP = """format flags
  gif        GIF  640x360
  gif-hd     GIF  1280x720   (default)
  video-hd   MP4  1920x1080  (looped 3x, needs ffmpeg)
  video-4k   MP4  3840x2160  (looped 3x, needs ffmpeg)
theme flags
  bg-black / fg-white   white drawing on black (default)
  bg-white / fg-black   black drawing on white
Flags can also be set with the STICKMAN_FLAGS environment variable."""


def _run(path, flags):
    os.environ["STICKMAN_FLAGS"] = " ".join(flags)       # read by stickman_anim at import time
    sys.argv = [path] + flags
    runpy.run_path(path, run_name="__main__")


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(USAGE)
        return 0
    cmd, rest = argv[0], argv[1:]
    if cmd == "version":
        from . import __version__
        print(__version__)
        return 0
    if cmd == "flags":
        print(FLAGS_HELP)
        return 0
    if cmd == "render":
        if not rest:
            print("stickman render: give a script path\n\n" + USAGE)
            return 2
        _run(rest[0], rest[1:])
        return 0
    if cmd == "demo":
        here = os.path.join(os.path.dirname(os.path.abspath(__file__)), "examples")
        names = sorted(f[:-3] for f in os.listdir(here) if f.endswith(".py") and not f.startswith("_"))
        pick = rest[0] if rest and rest[0] in names else "pr_review"
        flags = rest[1:] if rest and rest[0] in names else rest
        _run(os.path.join(here, pick + ".py"), flags)
        return 0
    print("stickman: unknown command %r\n\n%s" % (cmd, USAGE))
    return 2
