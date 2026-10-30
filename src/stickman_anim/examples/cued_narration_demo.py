"""Phase E Audio Cues, Multi-Speaker, and SFX Demo.

Demonstrates:
- Script @cue(name) marker parsing and frame triggers.
- Action synchronization at exact voiceover moments.
- Procedural sound effect generation (pop, ding, whoosh).
"""
import os
import math
from stickman_anim import *
from stickman_anim.audio_fx import parse_cued_script, CueTimeline, synthesize_sfx

N = 36

# Narration script with embedded animation cues
SCRIPT = "Starting up the server. @cue(activate) Systems online! @cue(celebrate) Launch complete!"

clean_text, cue_fracs = parse_cued_script(SCRIPT)
timeline = CueTimeline(cue_fracs, total_frames=N)


def render(f):
    c = Frame(f)
    t = float(f)
    c.background("chalkboard")
    c.floor(310)

    # Robot agent standing near server
    c.character(160, 310, kind="server_bot", scale=1.0)

    # Human developer
    if not timeline.has_fired("activate", f):
        # Waiting / thinking
        c.character(340, 310, kind="human", action="think", t=t)
        c.emote((340, 215), kind="?")
    elif not timeline.has_fired("celebrate", f):
        # Pointing and working
        c.character(340, 310, kind="human", action="point", t=t, accessories=["glasses"])
        c.emote((340, 215), kind="!")
        # Circuit activity lines
        c.line((180, 260), (320, 260), col=(80, 220, 255), w=2.0)
    else:
        # Celebration jump!
        c.character(340, 310, kind="human", action="celebrate", t=t, accessories=["crown"])
        impact_t = (f - timeline.frame_at("celebrate")) * 0.1
        c.confetti((340, 200), t=impact_t, count=25)
        c.emote((340, 215), kind="heart")

    # Display active cues
    if timeline.is_active("activate", f, window=6):
        c.text((320, 80), ">> CUE: ACTIVATE <<", font(14), (80, 220, 255), "mm")
    elif timeline.is_active("celebrate", f, window=8):
        c.text((320, 80), ">> CUE: CELEBRATE <<", font(14), (90, 255, 140), "mm")

    c.text((320, 32), "Phase E: Audio Cues & Narration Sync", font(18), WHITE, "mm")
    return c.image()


if __name__ == "__main__":
    main(render, N, "cued_narration_demo", [0, 10, 20, 30])
