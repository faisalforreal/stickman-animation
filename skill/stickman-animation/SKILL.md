---
name: stickman-animation
description: Make hand-drawn, stop-motion style stickman animations as GIF or MP4 video (white line art on black by default, or black on white; HD or 4K) with optional voice narration (TTS via Gemini Charon, OpenAI, or custom endpoint) and viral animated captions (Hormozi, MrBeast, Ali Abdaal, Dev minimal, or 400+ CapCut styles burned into MP4 via FFmpeg). Use this skill whenever the user asks for stickman / stick figure / stop-motion / whiteboard-style explainer animations, wants voiceover narration or subtitles added to stick figure videos, wants robot-stickman "AI agents" shown doing work, or wants to visualise software or business workflows. Also use it for follow-up edits (change text, adjust voice, tweak caption style or position, change colors).
---

# Stickman stop-motion animation with Voice & Captions

Produces short looping animations (GIF or MP4, HD 1280x720 by default) in one consistent visual language: jittery line art with cyan/green accents, white on black by default or black on white.

Now enhanced with **flexible TTS narration** (Gemini 3.8 Flash TTS with voice `Charon`, OpenAI, ElevenLabs, or custom REST endpoints) and **retention-engineered dynamic captions** (integrated AutoCaptions engine with 400+ CapCut and viral creator presets).

---

## 1. Voice Narration (TTS)

Narration is configured via `.env` (or environment variables) without changing code:
```env
TTS_PROVIDER=gemini               # 'gemini' (default), 'openai', 'elevenlabs', or 'custom'
TTS_API_KEY=your_key_here         # Your Gemini or provider API key
TTS_MODEL=gemini-3.8-flash-tts    # Model name
TTS_VOICE=Charon                  # Voice: Charon (default), Puck, Kore, Fenrir, Aoede
TTS_ENDPOINT=                     # Optional custom REST endpoint URL
```

### Generating Voiceover:
- **CLI**:
  ```bash
  stickman voice "AI agents write code, test it, and open a PR." --output speech.wav
  ```
- **Python**:
  ```python
  from stickman_anim.tts import generate_speech, get_audio_duration
  audio_path = generate_speech("AI agents write code, test it, and open a PR.", voice="Charon")
  duration = get_audio_duration(audio_path)
  ```

---

## 2. Animated Captions & Style Presets

Captions are burned directly into MP4 videos using FFmpeg `libass` with active-word color highlights, spring-bounce scaling, and modern rounded badge backdrops.

### Default Caption Placement:
- **`pos_y = 75.0`**: Positioned **75% from the top (25% from bottom)**. This keeps the central animation stage completely clear while ensuring high subtitle readability.
- Override anytime via `--pos-y <PERCENT>` or in Python.

### Curated Style Presets:
| Preset | Visual Description | Best For |
|---|---|---|
| `hormozi-bold` *(Default)* | Massive bold uppercase, vibrant electric yellow highlight (`#FFE600`), thick black outline | High retention viral explainers |
| `mrbeast-pop` | Comic impact stroke, bright neon green highlight (`#2BF82A`), explosive energy | Engaging workflow beats |
| `ali-abdaal-clean` | Dark rounded pill badge, sky blue highlight (`#38BDF8`), elegant typography | Educational and professional videos |
| `dev-minimal` | Monospace terminal badge, emerald green highlight (`#10B981`) | Developer tools and code workflows |
| `cyberpunk-neon` | Electric cyan ground, glowing neon pink highlight (`#FF0080`) | Tech and gaming workflows |
| `karaoke-gold` | Dim inactive words swept by continuous gold wipe (`#FFD700`) | Music and steady pacing |
| `luxury-editorial` | Champagne gold serif typography (`#D4AF37`) | High-end presentations |
| `bold_red_accent` | Crisp white typography with crimson red highlight (`#FF2020`) | Clear punchy alerts |

*Run `stickman presets` or `list_presets()` to search the complete catalog of 400+ presets.*

---

## 3. One-Call Voiced & Captioned Animation Workflow

The quickest way to render a fully voiced, synchronized, and captioned animation is `export_with_voice`:

```python
from stickman_anim import *

def render(f):
    c = Frame(f)
    c.floor(322)
    c.robot(160, 322, eye=CYAN, hr=(220, 260))
    c.human(480, 322, thumbs_up=True)
    c.text((320, 50), "AI Review Pipeline", font(20), WHITE, "mm")
    return c.image()

if __name__ == "__main__":
    script = "AI agents write code and run tests. A human engineer reviews and approves."
    export_with_voice(
        render=render,
        script_text=script,
        name="review_pipeline",
        style="hormozi-bold",     # Subtitle style
        pos_y=75.0,               # 75% down from top
        voice="Charon",           # Narration voice
        ms=120                    # 120ms per frame
    )
```

This automatically:
1. Generates speech with `Charon` via Gemini TTS.
2. Synchronizes the total animation frame count to match the audio duration.
3. Renders the stickman visual frames into MP4.
4. Burns styled subtitles with active-word highlights at 75% down the screen.
5. Muxes speech audio and writes `review_pipeline.mp4`.

---

## 4. Visual Style Rules

- **Black background with white 2.6px lines (default; `bg-white` flips to black on white), round caps.**
- **Stop-motion boil.** Every primitive jitters its points by about 1.2px, seeded by the frame number.
- **Colour means state**: grey/dim = idle, cyan = working/active, green = done/success, red = failure.
- **Two kinds of characters**: AI agents are *robot-stickmen* (square head, eyes, mouth grille, antenna: `robot()`); people are *round-head stickmen* with glasses (`human()`).
- **No brand logos**: Label windows with plain text instead of logos.

---

## 5. CLI Commands

```bash
# Render bundled demos
stickman demo pr_review video-hd

# Generate speech narration
stickman voice "Automation complete" --output speech.wav --voice Charon

# Burn styled subtitles into existing video
stickman caption my_video.mp4 --text "Spoken script" --style hormozi-bold --pos-y 75

# Explore 400+ subtitle presets
stickman presets --search neon
stickman presets --category minimal
```
