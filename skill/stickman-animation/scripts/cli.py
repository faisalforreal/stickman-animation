"""Command line: `stickman demo|render|voice|caption|presets|flags|version`."""
import os
import runpy
import sys
import argparse

USAGE = """usage: stickman <command> [flags / options]

commands:
  demo [name] [flags]       render a bundled example (pr_review, fewer_devs, ci_pipeline)
  render SCRIPT [flags]     run your own script with format / theme / tts flags applied
  voice TEXT [options]      generate speech audio using configured TTS (Gemini/OpenAI/Custom)
  caption VIDEO [options]   burn styled subtitles & audio into a video (AutoCaptions engine)
  presets [options]         list available subtitle style presets (400+ CapCut styles)
  flags                     list the format and theme flags
  version

visual flags (any order):
  gif | gif-hd | video-hd | video-4k            output format   (default gif-hd)
  bg-black (=fg-white) | bg-white (=fg-black)   colour theme    (default bg-black)

voice & caption options:
  --tts "Text to say"       generate speech and synchronize animation duration
  --voice NAME              voice name (default Charon)
  --style NAME              caption preset style (default hormozi-bold)
  --pos-y PERCENT           caption vertical position (default 75: 75% from top)

examples:
  stickman demo pr_review video-hd bg-white
  stickman voice "Hello agents" --output hello.wav
  stickman caption video.mp4 --text "Spoken text" --style hormozi-bold --pos-y 75
  stickman demo pr_review video-hd --tts "Agent opens a PR" --style hormozi-bold
"""

FLAGS_HELP = """format flags:
  gif        GIF  640x360
  gif-hd     GIF  1280x720   (default)
  video-hd   MP4  1920x1080  (looped 3x, needs ffmpeg)
  video-4k   MP4  3840x2160  (looped 3x, needs ffmpeg)

theme flags:
  bg-black / fg-white   white drawing on black (default)
  bg-white / fg-black   black drawing on white

voice & caption flags:
  --tts "text"          generate narration audio and sync frames
  --voice NAME          voice name (default Charon)
  --style NAME          caption style (hormozi-bold, mrbeast-pop, ali-abdaal-clean, etc.)
  --pos-y PERCENT       caption vertical distance from top (default 75)
"""


def _run(path, flags):
    os.environ["STICKMAN_FLAGS"] = " ".join(flags)       # read by stickman_anim at import time
    sys.argv = [path] + flags
    runpy.run_path(path, run_name="__main__")


def _cmd_voice(args):
    from .tts import generate_speech
    parser = argparse.ArgumentParser(prog="stickman voice", description="Generate speech narration audio.")
    parser.add_argument("text", help="Text to convert to speech")
    parser.add_argument("-o", "--output", help="Output audio file path (.wav or .mp3)")
    parser.add_argument("-v", "--voice", default="Charon", help="Voice identifier (default: Charon)")
    parser.add_argument("-m", "--model", help="Model name (e.g. gemini-3.8-flash-tts)")
    parser.add_argument("-p", "--provider", help="TTS provider (gemini, openai, elevenlabs, custom)")
    opts = parser.parse_args(args)

    out = generate_speech(
        opts.text,
        output_path=opts.output,
        voice=opts.voice,
        model=opts.model,
        provider=opts.provider,
    )
    print(f"wrote audio: {out}")
    return 0


def _cmd_caption(args):
    from .captions import add_captions
    parser = argparse.ArgumentParser(prog="stickman caption", description="Burn styled subtitles and audio into video.")
    parser.add_argument("video", help="Input video file path (.mp4)")
    parser.add_argument("-a", "--audio", help="Optional narration audio file (.wav, .mp3)")
    parser.add_argument("-t", "--text", help="Script text for timing alignment")
    parser.add_argument("-s", "--style", default="hormozi-bold", help="Subtitle preset style (default: hormozi-bold)")
    parser.add_argument("-y", "--pos-y", type=float, default=75.0, help="Vertical position in percent from top (default: 75.0)")
    parser.add_argument("-o", "--output", help="Output video path")
    opts = parser.parse_args(args)

    out = add_captions(
        opts.video,
        audio_path=opts.audio,
        script_text=opts.text,
        style_name=opts.style,
        pos_y=opts.pos_y,
        output_path=opts.output,
    )
    print(f"wrote captioned video: {out}")
    return 0


def _cmd_presets(args):
    from .presets import list_presets
    parser = argparse.ArgumentParser(prog="stickman presets", description="List available caption style presets.")
    parser.add_argument("-s", "--search", help="Search presets by keyword or ID")
    parser.add_argument("-c", "--category", help="Filter by category (curated, lyrics, bold, minimal, etc.)")
    opts = parser.parse_args(args)

    presets = list_presets(search=opts.search, category=opts.category)
    print(f"Available Presets ({len(presets)} found):")
    print(f"{'ID / Name':<28} {'Category':<12} {'Highlight':<10} {'Box':<6} {'Effect':<14} {'Pos Y':<6}")
    print("-" * 80)
    for p in presets[:35]:  # Display top matches
        print(f"{p['id'][:26]:<28} {p.get('category', '')[:10]:<12} {p.get('highlight_color', ''):<10} {str(p.get('has_box', False)):<6} {p.get('effect_type', ''):<14} {p.get('pos_y', 75.0):<6.0f}")
    if len(presets) > 35:
        print(f"... and {len(presets) - 35} more presets. Use --search <term> to filter.")
    return 0


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
    if cmd == "voice":
        return _cmd_voice(rest)
    if cmd == "caption":
        return _cmd_caption(rest)
    if cmd == "presets":
        return _cmd_presets(rest)
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
