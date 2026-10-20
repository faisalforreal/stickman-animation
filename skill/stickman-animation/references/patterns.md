# Scene patterns (640x360 canvas, floor line at y=322)

Each recipe lists layout coordinates that are known to work, the timeline shape, and the library calls. Mix and match: most good animations are one pattern plus a title.

## Contents
1. Title + tracker (multi-scene explainers)
2. Chat windows -> agent(s)
3. Stage pipeline / orchestrator
4. Kanban board
5. Branch graph + pull request
6. Diff review (reviewer, fixer)
7. Desk + monitor (coding, human reviewing)
8. Hub avatar (user-supplied picture)
9. Finale beat

---

## 1. Title + tracker (multi-scene explainers)
Use when the user lists 5+ sequential steps (dev workflow, onboarding...). One scene per step; scene durations in a list `DURS = [18, 14, ...]`, `STARTS = cumulative`.
- Title: `c.typed((320, 62), TITLE, font(20), WHITE, clamp((r+1)/6), "mm")`, 6 frames to type, then hold.
- Tracker: 7 circles at `x = 70 + i*83.3, y = 24`, joined by lines. Done = green filled circle + dark check; active = cyan ring (radius pulses +1 on odd frames) + centre dot; pending = dim ring.
- Scene art lives in y = 90-322. Robot at one side, big prop (board, panel, monitor) at the other.
- Final "Shipped" beat after the last scene: tracker all green, title turns green, sparkles.

## 2. Chat windows -> agents
Two windows stacked on the left (`window((14,16),(172,116),"Discord")`, second at y=130); agent(s) right.
- Per channel timeline from `t0`: type command 14 frames (cyan border while typing) -> packet flies window -> agent 6-8 frames (`arc_lerp`, height ~10-12) -> agent works 28 frames (cyan eyes, hands busy, progress bar) -> reply packet back (green) -> green reply bubble with check. Offset the second channel by 10-24 frames.
- Command text in the bubble, right-aligned inside the window; sender is a tiny round head + stub body left of the bubble.
- Commands like `@agent deploy v2`, `/report sales`. Label windows with plain text only.

## 3. Stage pipeline / orchestrator
Row of `node()` boxes at y~270 (6 nodes: x = 70 + i*100, w=84, h=36) or y~140 for 4 nodes (x = 150,270,390,510). Arrows between nodes turn green when the left node is done.
- Orchestrator is either a bigger robot with a console (rect 72x14) and a dispatch "bus" line (vertical + horizontal DIM, pulse cyan toward the active stage for the first 4-6 frames), or an avatar badge (pattern 8).
- Stage state function: `idle` before start, `run` between start and end, `ok` after. A *fail* beat: stage goes `fail` (red, flicker colour on odd frames) for ~5 frames while the robot "fixes" (hands at a log panel, cyan sparks), then re-runs and goes green. Put an explanatory line in a log panel under the nodes ("Error: test failed" -> "All checks passed").
- A ticket (small rect with 2 lines) travelling along the stages shows hand-offs: hold at stage, lerp with `arc_lerp` between.

## 4. Kanban board
Three column rects x0 = 160 + c*150, width 140, y 100-310, header line at y=126, headers "To Do / In Progress / Done". Cards 116x34 with `#101` label + a grey bar. Card colour follows its column: white -> cyan -> green. Cards appear (born frame), then move between slots via `lerp` over 2-3 frames. Robot at x~100 with the right hand following the moving card (`hr=(card.x-4, card.y+17)`).

## 5. Branch graph + pull request
Main line y=275 (white) with 2 dots; feature branch leaves at x=250 up to y=215 (cyan polyline) and gains 3 commit dots over ~6 frames; PR card (130x56, text "Pull Request") appears top-right with an arrow from the last commit; tag "Open" turns "Approved"/"Merged" green. Robot on the left with both hands typing.

## 6. Diff review (reviewer, fixer)
Panel (250,100)-(610,300), six lines `y = 128 + i*28`: neutral (grey bar), added (green `+` and bar), removed (red `-` and bar). Reviewer: magnifier (circle r13 + handle) descends the lines while comment bubbles (48x20 rect + tail + two lines, cyan) appear at flagged lines. Fixer: hand at flagged line, bar re-drawn shorter, bubble turns green with a check, final cheer.

## 7. Desk + monitor (coding, human reviewing)
Desk line y=262 with legs; monitor rect (170,100)-(470,250) with stand. Code lines: cyan bars of varying length/indent revealed over time with a blinking cursor; done = all green + check above monitor. Robot stands beside the desk (hand to keyboard `(x, 256 - wig)`). Human sits at the desk end: head circle with glasses, torso to hips, thigh left under desk, calf down, chair lines DIM; mouse hand wiggles during the click.
- "Human verifies PR": highlight scanner (cyan rect) steps down diff lines; checklist items (`Tests pass`, `Logic OK`, `Secure`) spin then check; cursor glides to an Approve button; status tag Open -> Approved -> Merged; green dot drops onto a `main` line; robot cheers; human thumbs up.

## 8. Hub avatar (user-supplied picture)
`av = load_avatar(path)`; `c.avatar(av, (320, 108), 50)` plus a pulsing ring: DIM/grey idle, cyan (+7px outer ring, radius +3 on odd frames) when busy, green when done. Label below: name (font 15) and a status line ("working: code"). Dashed/cyan dispatch lines from the avatar down to the active stage node. Reply packets go back to the chat windows. Use the picture as-is; don't state who it depicts unless the user does.

## 9. Finale beat
Hold 6-10 frames: everything green, characters cheering (`robot(cheer=True)`, `human(thumbs_up=True, smile=True)`), 3-5 sparkles that toggle with `(f + x) % 3 == 0`, optional "Done"/"Shipped" word in green. Place the check/word away from other labels (check overlap in the contact sheet).
