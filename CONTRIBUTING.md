# Contributing

- `pip install -e ".[dev]"` then `pytest`. MP4 tests need `ffmpeg` on your PATH; they skip without it.
- The library is one file: `src/stickman_anim/lib.py`. The Claude skill ships an identical copy as
  `skill/stickman-animation/scripts/stickman_lib.py`; after editing run `python tools/sync_skill.py`
  (a test fails if they drift).
- Keep new drawing helpers in the same style: every primitive goes through the jittered `Frame` methods,
  colours come from the palette (`WHITE` means "ink", never hard-code black or white), layouts stay in
  the 640x360 logical canvas.
- Add a scene recipe to `skill/stickman-animation/references/patterns.md` or an example under
  `src/stickman_anim/examples/` if you build something reusable. Look at the contact sheet in both themes.
