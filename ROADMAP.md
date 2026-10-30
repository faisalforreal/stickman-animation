# Stickman Animation Universal Engine Upgrade Roadmap

This roadmap tracks the step-by-step implementation of the Universal Generator-Driven Animation Studio.
Order of execution: **A → B → C → E → D → G → F → H → I**.

---

## [x] Phase A: Universal Drawing Layer
- [x] A1. Path engine: Béziers (cubic/quad), arcs, Catmull-Rom splines, pressure-tapered strokes, rough.js sketchy rendering, frame-seeded boil (`paths.py`)
- [x] A2. Draw-on animation: 0..1 arc-length reveal along stroke order + optional pen/hand cursor
- [x] A3. SVG importer: Parse paths, groups, transforms, shapes into strokes + hatch/scribble fills (`svg_import.py`)
- [x] A4. Icon packs: `c.icon("name")` with 200+ offline bundled Lucide/Tabler icons + on-demand CDN cache (`icons.py`)
- [x] A5. Fill styles: hatch, crosshatch, stipple, scribble, wobbly solid (`paths.py`)
- [x] A6. Image to line art: DoG/Sobel edge detection + contour tracing to hand sketch (`generators.py`)
- [x] A7. LLM sketch DSL: Compact JSON stroke/shape spec compiler (`generators.py`)
- [x] A8. Text as pen strokes: True shaped stroke writing (Latin & Bangla) (`generators.py`)
- [x] A9. LaTeX/math renderer: Math expressions to vector hand-drawn strokes (`generators.py`)
- [x] A10. Diagram generators: Mermaid (flowchart & sequence) & auto-DAG layout (`diagrams.py`)
- [x] A11. xkcd-style charts: Bar, line, pie, scatter, Sankey (`diagrams.py`)
- [x] A12. Annotations: Hand-drawn circle, underline, highlight, bracket, curly arrow (`generators.py`)
- [x] A13. Other assets: UI mockups (browser, phone, terminal, code block) & paper backgrounds (`generators.py`)

## [x] Phase B: Articulated Characters & Lip-Sync
- [x] B1. 2D skeleton rig with forward kinematics & 2-bone analytic IK (`rig.py`)
- [x] B2. 12+ named poses/actions: walk, run, wave, point, type, sit, shrug, jump, celebrate, fail, hold, hand-off, think
- [x] B3. Facing and flip, prop attach points (hands/head), and accessories (hats, headphones, tie, cape, badge)
- [x] B4. Expressions, eye look-at tracking, and audio amplitude-driven mouth movement (lip-sync)
- [x] B5. Emotes (`!`, `?`, heart, sweat, zzz), speech bubbles, thought bubbles, and crowds

## [x] Phase C: Motion, Easing, Particles & Camera
- [x] C1. Easing library: cubic, back overshoot, elastic, bounce, spring, stagger, squash & stretch (`motion.py`)
- [x] C2. Keyframe tracks (`Track`) for scalars and points
- [x] C3. Deterministic particles (confetti, sparks, smoke, rain) & speed lines
- [x] C4. Virtual camera: pan, zoom, shake, follow, multi-plane parallax
- [x] C5. Scene transitions: wipe, iris, ink splash, zoom-through, page turn

## [x] Phase E: Audio Cues, Multi-Speaker & SFX
- [x] E1. `@cue(name)` script marker parser and exact frame alignment (`audio_fx.py`)
- [x] E2. Multi-speaker dialogue generation with speaker lip-sync routing (`audio_fx.py`)
- [x] E3. Procedural CC0 sound effects synthesizer (pop, click, whoosh, ding, pen scratch) & BGM auto-ducking + loudnorm

## [x] Phase D: Multi-Scene Timeline, Caching & Performance
- [x] D1. Multi-scene `Timeline` & `project.json` runner with transitions and B-roll/PiP (`timeline.py`)
- [x] D2. Hash-based scene render cache (`.stickman_cache/`)
- [x] D3. Windows/macOS ThreadPool multiprocessing fix + FFmpeg GPU encoder auto-probe
- [ ] D4. Aspect presets (`16:9`, `9:16`, `1:1`) with safe-zone caption placement

## [ ] Phase G: Agent Layer (Storyboard, Linter, Assets)
- [ ] G1. Declarative Storyboard JSON runner (`storyboard.py`)
- [ ] G2. Automated Self-QA bounding-box linter (off-canvas, text overlap, caption collision) (`qa.py`)
- [ ] G3. Searchable asset index CLI (`stickman assets`)
- [ ] G4. Restructured `SKILL.md` decision tree + cookbooks

## [ ] Phase F: Caption Upgrades
- [ ] F1. Auto emphasis and keyword emoji injection
- [ ] F2. Sidecar `.srt` and `.vtt` export
- [ ] F3. Stage collision avoidance & 9:16 safe zones

## [ ] Phase H: Export & Distribution
- [ ] H1. Social export presets (YouTube, Shorts, Reels, X, LinkedIn), WebM/MOV transparency
- [ ] H2. Animated SVG exporter (self-contained CSS path animation)
- [ ] H3. Auto-Thumbnail generator (`<name>_thumb.png`)

## [ ] Phase I: Quality, Licenses & Antigravity Sync
- [ ] I1. Asset license manifest (`LICENSES.md`)
- [ ] I2. Pytest suite coverage across all phases (all passing)
- [ ] I3. Full Antigravity global skill sync & validation
