---
name: stickman-animation
description: Make hand-drawn, stop-motion style black-and-white stickman animations as GIF or MP4 video (white line art on black by default, or black on white; HD or 4K; no voiceover) that explain a workflow, process or idea - e.g. "AI agents coding", "company workflow run by agents", "people in Discord/Telegram commanding agents", "agent opens a PR and a human approves it", dev pipelines, kanban boards, step-by-step explainers. Use this skill whenever the user asks for a stickman / stick figure / stop-motion / whiteboard-style / black background animation or GIF, wants robot-stickman "AI agents" shown doing work, or wants to visualise a software or business workflow as a short looping animation, even if they don't say "skill" or name the style. Also use it for follow-up edits to such a GIF (change text, add a stage, swap characters, translate labels, use their own avatar image).
---

# Stickman stop-motion animation

Produces short looping animations (GIF or MP4, HD 1280x720 GIF by default, ~8-14 s) in one consistent visual language: jittery line art with cyan / green accents, white on black by default or black on white. The look is "someone redrew every frame by hand", which comes from re-jittering every line each frame. The workflow below is what worked repeatedly; the bundled library does the drawing so you can spend your effort on the story.

## Flags: output format and colour theme

Both are chosen with plain words on the script's command line (or in the `STICKMAN_FLAGS` env var). `stickman_lib` reads them when it is imported, so scripts need no extra code: call `export()` and `sheet()` and the flags decide the rest. Map what the user asks for to flags:

| Flag | Output |
|---|---|
| `gif` | GIF, 640x360 (smallest file) |
| `gif-hd` | GIF, 1280x720 (**default**) |
| `video-hd` | MP4, 1920x1080, looped 3x |
| `video-4k` | MP4, 3840x2160, looped 3x |
| `bg-black` (or `fg-white`) | white drawing on black (**default**) |
| `bg-white` (or `fg-black`) | black drawing on white; accents are darkened so cyan/green/red stay readable |

Example: `python make_x.py video-4k bg-white`. Naming only `fg-black` implies `bg-white` and vice versa; a clashing pair (`bg-white fg-white`) stops with an error. When the user says things like "4K video", "white background", "HD gif", pick the matching flags yourself and tell them which you used. If they say nothing, use the defaults. In the script, end with the standard block (it keeps the guard that lets the multi-process renderer import the file):

```python
if __name__ == "__main__":
    main(render, N, "x", [8, 30, 60, 90])   # writes x_sheet.png (contact sheet) and x.gif or x.mp4 per the flags
```

`main()` takes the output name from the first non-flag command-line word. Rendering uses up to 4 processes on Linux; frames depend only on their number, so the result is identical.

Check the contact sheet in the chosen theme: on `bg-white` idle outlines are light grey and accents are deeper, so look again for contrast. Colour names stay the same in code (`WHITE` means "ink": near-black on a light ground; `BG` is the ground), so the same script works in both themes. Never hard-code `(0,0,0)` or `(255,255,255)` in a script.

## Style rules (and why)

- **Black background with white 2.6px lines (default; `bg-white` flips to black on white), round caps.** High contrast reads well as a small GIF, and a single stroke weight keeps it cohesive.
- **Stop-motion boil.** Every primitive jitters its points by about 1.2px, seeded by the frame number. Without this it looks like vector graphics; with it, it looks hand-drawn. The library does this for you, so draw everything through `Frame`.
- **Colour means state**: grey/dim = idle, cyan = working/active, green = done/success, red = failure (rare, only for a deliberate error beat). Colour is never decoration, so viewers learn the code in two seconds.
- **Two kinds of characters.** AI agents are *robot-stickmen* (square head, eyes, mouth grille, antenna: `robot()`); people are *round-head stickmen* with glasses (`human()`). The contrast is what makes "human verifies the agent" legible without words.
- **No voiceover, minimal text.** Short labels only (stage names, a typed command, "Done"). Type text in with a typewriter effect so the eye is led along.
- **Always loop cleanly.** End on a held "all green + sparkles" beat (4-10 frames), and make the first frame the idle/blank state.
- **No brand logos or copyrighted characters.** Label windows with plain text ("Discord", "Telegram") instead of drawing logos or mascots. If the user supplies their own picture (e.g. an agent avatar) use it as-is in a round badge; don't claim to know who it depicts.

## Workflow

1. **Pin down the story** in one sentence per stage (who acts, what moves, what the end state is). If the user lists steps, one step = one scene or one node. If they list nothing, pick 3-6 stages. Don't ask clarifying questions for simple requests; make a sensible version and offer tweaks afterwards.
2. **Pick a layout pattern** from `references/patterns.md` (chat windows -> hub, stage pipeline, kanban, branch/PR graph, diff review, hub-and-spoke orchestrator, single desk scene). Reuse them; they are already tuned to 640x360.
3. **Write a timeline first.** Define phase start frames as constants (`T_TYPE, T_SEND, T_WORK, T_DONE`...). Roughly: typing 12-16 frames, a packet flight 6-8, a stage 8-16, final hold 6-10. Total 70-120 frames at 120 ms. Everything in `render(f)` derives from `f` and those constants, so you can re-time by editing numbers.
4. **Write the script** at `<scratch>/make_xxx.py`: `sys.path.insert(0, "<this skill>/scripts")`, `from stickman_lib import *`, define `render(f)` using `Frame(f)`, then end with the `if __name__ == "__main__": main(render, N, "x", [frames to eyeball])` block (this follows the format and theme flags). `scripts/example_demo.py` is a ~70-line template. Run scripts as `python make_x.py <flags>`.
5. **Look before you ship.** Render, open the contact sheet with Read, and check: text isn't clipped or overlapping (typewriter frames excepted), arms don't stretch absurdly (keep hands within about 70px of the shoulder, or move the character), nothing sits on top of a label, the final frame is clean. Fix and re-render; one or two iterations is normal.
6. **Deliver** the file with `SendUserFile` (display "render" for a GIF, "attach" for a large MP4); say which format and theme flags you used. In the reply: say what happens in 3-5 short bullets, note anything you substituted (e.g. no logos), and offer 2-3 concrete tweaks. Don't paste code.

## Library cheat sheet (`scripts/stickman_lib.py`)

`Frame(f)` -> draw -> `.image()`. Constants: `WHITE GREY DIM CYAN GREEN RED`, canvas `W,H = 640,360`.

- Primitives: `line poly rect circle dashed text typed wipe`; `font(size, bangla=False)`
- Icons: `spinner check cross sparkle packet floor`
- Characters: `robot(cx, floor_y, eye, hl, hr, cheer)`, `human(cx, floor_y, hl, hr, thumbs_up, smile)`; `hl/hr` are absolute hand targets, `None` = idle arm; use `c.wig` for typing wobble
- Furniture: `window(a, b, title)`, `node(center, w, h, label, state)`, `avatar(PIL_image, center, radius)` + `load_avatar(path)`
- Motion helpers: `lerp clamp arc_lerp along`
- Flags: `FORMAT`, `THEME`, `describe()`; `main(render, n, name, sheet_frames)` for the standard script ending, or `export(render, n, base, ms, workers=)` and `sheet(render, idxs, path)` separately; `iter_frames(render, n, workers)`
- Resolution (only for manual overrides; the format flag already sets it): `set_quality("sd"|"hd"|"fhd"|"4k")`
- Output: `save_gif(frames, path, ms=120, colors=64)`, `save_mp4(frames, path, ms=120)` / `render_mp4(render, n, path, ms=120)` (crisp video; use `render_mp4` at 4K, `export()` already does), `contact_sheet(frames, idxs, path)`

## Gotchas learned the hard way

- **Bangla / non-Latin text**: use `font(size, bangla=True)` (FreeSans, shaped through raqm) and reveal with `wipe()`, not character slicing, because slicing breaks conjuncts. Split long lines in two; about 30 glyphs at 50px fills the width. Translate faithfully and mention the translation in the reply.
- Typewriter on a centered title: compute position from the *full* string so the text doesn't slide as it grows.
- Parallel actors look alive when **staggered** (offset each by 8-24 frames); synchronous ones look robotic.
- Use `f % 2` alternation for typing hands, and a one-frame blink every ~14 frames; tiny details sell "alive".
- Keep per-frame draw calls modest (<~600 primitives); 100+ frames render in a few seconds at S=2. If a scene is dense, drop `S` to 1.5 rather than cutting content.
- GIF palette: stay with the fixed palette above; extra greys add file size without adding clarity. 1-3 MB is normal.
- **Resolution**: layouts are always authored on a 640x360 logical canvas; `set_quality()` only changes how many pixels draw it, so the same coordinates stay sharp at any size. Default is **HD 1280x720** (supersampled 4x, then downsampled, so edges are anti-aliased). Presets: `sd` 640x360 (~0.7 MB, only if the user needs a tiny file), `hd` 1280x720 (~2-7 MB), `fhd` 1920x1080 (~3-12 MB), `4k` 3840x2160. Rendering time grows with resolution (HD ~20 s for 130 frames, FHD roughly 2-3x). If the user asks for "higher resolution", "sharper", "HD", "full HD" or "4K", call `set_quality` with that preset; no layout changes needed.
- **GIF vs MP4**: GIFs are capped at 256 colours and get heavy at FHD/4K. `save_gif` already uses a 64-colour palette with no dithering, which suits this black/white/cyan/green art. When the user wants the sharpest result, for a video edit or a social post, also write `save_mp4(frames, path, ms)` (H.264, 3 loops, 30 fps) and send both. For 4K, deliver an MP4 (or a PNG still) rather than a GIF. At 4K never keep all frames in a list (about 25 MB each, it gets the process killed): call `set_quality("4k")` then `render_mp4(render, N, "out.mp4", 120)`, which streams frames into ffmpeg and loops the clip 3x. A 140-frame 4K clip takes about 2.5 minutes and gives a ~13 MB file.
- **4K stills for a video frame**: `set_quality("4k")`, build one `Frame(37)` (any fixed number gives the same jitter) and `c.image().save("frame.png")`. Keep the frame number fixed so re-renders match.
- Look at the contact sheet (it is downscaled to 640 px per tile, so it stays small however high the render resolution is) and, at least once, crop a region of a full-resolution frame to check text edges.
- If you can't find fonts, `find_font()` falls back to DejaVu; check `fc-list` if text renders as boxes.
