---
name: stickman-animation
description: Make hand-drawn, stop-motion style stickman animations as GIF or MP4 video (white line art on black by default, or black on white; HD or 4K) with optional voice narration (TTS via Gemini Charon, OpenAI, or custom endpoint) and viral animated captions (Hormozi, MrBeast, Ali Abdaal, Dev minimal, or 400+ CapCut styles burned into MP4 via FFmpeg). Use this skill whenever the user asks for stickman / stick figure / stop-motion / whiteboard-style explainer animations, wants voiceover narration or subtitles added to stick figure videos, wants robot-stickman "AI agents" shown doing work, or wants to visualise software or business workflows. Also use it for follow-up edits (change text, adjust voice, tweak caption style or position, change colors).
---

# Universal Hand-Drawn Stickman Animation Engine

`stickman-animation` generates stop-motion whiteboard and hand-drawn animations (GIF or MP4, HD 1280x720 / 4K / 9:16 Shorts) in a consistent visual aesthetic: jittery sketch lines, rough.js bowing, double-strokes, and vibrant accents (cyan, green, yellow, red).

It includes a universal vector drawing layer, articulated 2-bone IK character rigging, virtual camera parallax, audio `@cue` synchronization, multi-speaker dialogue, procedural SFX, multi-scene timeline with safe caption zones, declarative JSON storyboards, and automated QA linting.

---

## 1. Quick Decision Tree

When fulfilling a user request, pick the best approach:
1. **Full Explainer Video from Prompt / Script** -> Use **Declarative Storyboard** (`storyboard.py` / `stickman storyboard`). Write scenes, narration, elements, and let the engine lint and render everything automatically.
2. **Specific Architecture / Flowchart** -> Use `c.mermaid("graph LR\nA --> B", box)` or `c.icon(name, center)` + `c.character(...)`.
3. **Data / Metrics Presentation** -> Use `c.chart_bar()`, `c.chart_line()`, or `c.chart_pie()`.
4. **Math / Science Explainers** -> Use `c.latex(r"E = mc^2", xy)` or `c.write_text()`.
5. **Character Performance & Acting** -> Use `c.character(kind="human"|"robot", action="walk"|"point"|"celebrate")`, with `c.emote()` and `c.speech_bubble()`.
6. **Multi-Scene Video with Transitions** -> Use `Timeline` (`timeline.py`) with `16:9` or `9:16` aspect presets and `wipe` or `iris` transitions.

---

## 2. Universal Drawing Layer (Phase A)

### Vector Paths & Whiteboard Draw-On
```python
from stickman_anim import *

p = Path()
p.move_to(50, 50).line_to(200, 50).cubic_to(250, 100, 250, 150, 200, 200).close()

# Draw with rough.js bowing, double strokes, or hatch fill
c.draw_path(p, col=CYAN, w=2.6, draw_on=0.8, pen=True, fill_style="hatch")
```

### Curated Icons (Lucide / Tabler / Phosphor)
Thousands of icons loaded offline or cached automatically from CDN:
```python
c.icon("github", (100, 100), size=48, col=WHITE)
c.icon("rocket", (200, 100), size=48, col=CYAN, draw_on=0.5, pen=True)
c.icon("database", (300, 100), size=48, col=GREEN)
```

### Diagrams (Mermaid) & Charts
```python
# Automatic DAG Sugiyama layout:
c.mermaid("""graph TD
A[Build Code] --> B{Run Tests}
B -->|Pass| C[Deploy]
B -->|Fail| D[Alert Team]""", box=(60, 60, 520, 200))

# xkcd-style hand-drawn charts:
c.chart_bar((80, 120, 240, 140), [("Python", 85), ("Rust", 95), ("Go", 80)], title="Throughput")
c.chart_line((360, 120, 240, 140), [10, 25, 45, 90], labels_x=["Q1", "Q2", "Q3", "Q4"], title="Growth")
```

### LaTeX Math & Hand-Drawn Annotations
```python
c.latex(r"\int_{0}^{\infty} e^{-x^2} dx = \frac{\sqrt{\pi}}{2}", (320, 100), size=24)
c.annotate_circle((140, 80, 120, 60), col=GREEN)
c.annotate_underline((200, 220), length=160, style="wave", col=CYAN)
c.arrow_curved((120, 150), (280, 240), bend=0.3)
```

### UI Mockups & Paper Backgrounds
```python
c.background("notebook")  # 'dark', 'light', 'notebook', 'blueprint', 'chalkboard', 'sepia', 'grid'
c.mockup_browser((60, 80, 520, 220), url="https://antigravity.dev")
c.mockup_terminal((80, 100, 480, 180))
c.mockup_phone((460, 60, 120, 240))
```

---

## 3. Articulated Characters & Rigging (Phase B)

Characters use 2-bone analytic Inverse Kinematics (IK), named procedural actions, accessories, and lip-sync.

```python
# Human developer pointing with coffee and glasses:
c.character(
    cx=200, fl=310,
    kind="human",
    action="point",
    t=f,
    accessories=["glasses", "hat"],
    props={"left": "coffee"}
)

# Robot AI agent with look-at tracking and audio-driven lip sync:
c.character(
    cx=440, fl=310,
    kind="robot",
    action="celebrate",
    t=f,
    look_at=(200, 240),
    mouth_open=0.75,
    accessories=["crown", "headphones"]
)

# Comic emotes and speech bubbles:
c.emote((200, 215), kind="!")        # '!', '?', 'heart', 'sweat', 'zzz'
c.speech_bubble((200, 200), "Deploy complete!", thought=False, progress=1.0)

# Procedural background crowd:
c.crowd((100, 220, 440, 90), count=6, action="celebrate", t=f)
```

**Supported Actions**: `walk`, `run`, `wave`, `point`, `type`, `sit`, `shrug`, `jump`, `celebrate`, `fail`, `hold`, `hand_off`, `think`.

---

## 4. Motion, Particles & Virtual Camera (Phase C)

### Easing & Physics
```python
from stickman_anim.motion import Track, Camera, squash_stretch, spring

# Keyframe track with back overshoot:
tr = Track([(0.0, 100.0), (1.0, 300.0)], easing="out_back")
x = tr.at(t)

# Spring physics and squash-stretch volume preservation:
sx, sy = squash_stretch(t, intensity=0.35)
```

### Particles & Speed Lines
```python
c.confetti((320, 180), t=0.5, count=30)
c.sparks((200, 250), t=0.3, count=20)
c.smoke((150, 300), t=0.4, count=10)
c.rain((0, 0, 640, 360), t=0.2, count=35)
c.speed_lines(direction="right", intensity=1.0)
```

### Virtual 2D Camera with Parallax
```python
cam = Camera(cx=320, cy=180, zoom=1.2)
cam.add_shake(amplitude=4.0)

# z = 0.3 moves slower (background); z = 1.0 is stage; z = 1.4 moves faster (foreground)
screen_pos = cam.world_to_screen((world_x, world_y), z=1.0, t=t)
```

---

## 5. Audio Cues, Multi-Speaker & SFX (Phase E)

### Script `@cue(name)` Synchronization
Embed animation cues inside narration scripts without altering what TTS speaks:
```python
script = "Initialize the server. @cue(start) System active! @cue(cheer) Mission complete."
clean_text, cue_fracs = parse_cued_script(script)
timeline = CueTimeline(cue_fracs, total_frames=N)

# Inside render(f):
if timeline.has_fired("cheer", f):
    c.character(320, 310, action="celebrate")
    c.confetti((320, 180))
```

### Multi-Speaker Dialogue
```python
dialogue_text = """
[Speaker: Charon] Welcome everyone to our agent workflow stream.
[Speaker: Puck] Excited to be here! Let's examine the pipeline.
"""
lines = parse_dialogue_script(dialogue_text)
master_audio, intervals = generate_dialogue_audio(lines, voice_map={"Charon": "Charon", "Puck": "Puck"})
```

### Procedural Sound Effects (Zero External Files)
Synthesize 16-bit 44.1kHz WAV effects directly in Python:
```python
synthesize_sfx("pop", "pop.wav")
synthesize_sfx("ding", "ding.wav")
synthesize_sfx("whoosh", "whoosh.wav")
synthesize_sfx("click", "click.wav")
synthesize_sfx("pen_scratch", "scratch.wav")
```

---

## 6. Multi-Scene Timeline & Aspect Presets (Phase D)

```python
from stickman_anim.timeline import Timeline, Scene

tl = Timeline(aspect="9:16", ms=120)  # '16:9' horizontal, '9:16' vertical Reels/Shorts, '1:1' square
tl.add_scene(Scene(name="problem", render_fn=scene1, frames=24, transition_to_next="wipe"))
tl.add_scene(Scene(name="solution", render_fn=scene2, frames=24, transition_to_next="cut"))

# Note: Subtitle safe zones are automatically adjusted:
# In 16:9, subtitles sit at 75% Y.
# In 9:16 vertical, subtitles sit at 64% Y to safely avoid TikTok/Reels UI buttons and engagement overlays.
tl.render_all("output.mp4", style="hormozi-bold")
```

---

## 7. Declarative Storyboard & Self-QA (Phases G & F)

The recommended workflow for autonomous AI coding agents:

```python
from stickman_anim.storyboard import render_storyboard

storyboard_spec = {
    "title": "Agent Demo",
    "aspect": "16:9",
    "style": "hormozi-bold",
    "scenes": [
        {
            "name": "intro",
            "frames": 24,
            "background": "dark",
            "narration": "Building software with autonomous stickman agents.",
            "elements": [
                {"type": "character", "cx": 200, "floor_y": 310, "kind": "human", "action": "point"},
                {"type": "icon", "name": "bot", "pos": [440, 160], "size": 48},
                {"type": "text", "pos": [320, 40], "text": "Autonomous Workflow"}
            ]
        }
    ]
}

# Automatically runs Self-QA bounding box check before rendering:
render_storyboard(storyboard_spec, "agent_demo.mp4", lint=True)
```

### CLI Subcommands
```bash
stickman storyboard story.json -o output.mp4   # Render declarative storyboard
stickman lint story.json                       # Check for off-canvas text, collisions, pacing
stickman assets "database"                     # Search bundled icons, poses, styles
stickman presets --search "bold"               # Search 400+ CapCut subtitle styles
```

---

## 8. Export Formats (Phase H)

- **Social Presets**: `export_social(video, "reels.mp4", platform="reels")`
- **Transparent Video**: `export_transparent_video(frames, "anim.webm", format_type="webm")`
- **Animated SVG**: `export_animated_svg(paths, "vector.svg", duration_sec=3.0)`
- **Auto-Thumbnail**: `generate_thumbnail(video, "thumb.png", title_badge="Featured Scene")`
