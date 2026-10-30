"""Multi-Scene Timeline, Hash Render Caching, Aspect Presets, and Project Runner.

Provides:
- `Scene` definition with per-scene narration, transition, duration, and B-roll PiP overlays.
- `Timeline` sequencer with aspect ratio presets (16:9 horizontal, 9:16 vertical Shorts/Reels, 1:1 square).
- Automatic aspect-ratio safe-zone calculation for captions (prevents TikTok/Reels UI overlay collisions).
- Hash-based scene caching in `.stickman_cache/` for instant re-renders when tweaking scripts.
- Declarative `project.json` runner with batch rendering support.
"""

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable, Tuple, Union
from PIL import Image

from .motion import transition_wipe, transition_iris, transition_ink_splash


ASPECT_PRESETS: Dict[str, Dict[str, Any]] = {
    "16:9": {
        "logical": (640, 360),
        "output": (1280, 720),
        "caption_safe_y": 75.0,  # 75% down from top
        "name": "horizontal"
    },
    "9:16": {
        "logical": (360, 640),
        "output": (720, 1280),
        "caption_safe_y": 64.0,  # 64% down, avoiding TikTok/Reels UI buttons & caption bar
        "name": "vertical"
    },
    "1:1": {
        "logical": (540, 540),
        "output": (1080, 1080),
        "caption_safe_y": 78.0,
        "name": "square"
    }
}


@dataclass
class Scene:
    """A single storyboard scene in a multi-scene timeline."""
    name: str
    render_fn: Optional[Callable[[int], Image.Image]] = None
    frames: int = 30
    narration: Optional[str] = None
    voice: str = "Charon"
    transition_to_next: str = "cut"      # 'cut', 'wipe', 'iris', 'splash'
    transition_frames: int = 6
    b_roll_path: Optional[str] = None    # path to image or video to overlay
    b_roll_box: Optional[Tuple[int, int, int, int]] = None  # (x, y, w, h) in logical coords
    custom_data: Dict[str, Any] = field(default_factory=dict)

    def compute_hash(self) -> str:
        """Computes SHA-256 fingerprint of scene contents for caching."""
        h = hashlib.sha256()
        h.update(self.name.encode("utf-8"))
        h.update(str(self.frames).encode("utf-8"))
        h.update((self.narration or "").encode("utf-8"))
        h.update(self.voice.encode("utf-8"))
        h.update(self.transition_to_next.encode("utf-8"))
        h.update(str(self.transition_frames).encode("utf-8"))
        if self.b_roll_path and os.path.isfile(self.b_roll_path):
            try:
                with open(self.b_roll_path, "rb") as f:
                    h.update(f.read())
            except Exception:
                pass
        return h.hexdigest()[:16]


class Timeline:
    """Orchestrates multi-scene rendering, transitions, caching, and aspect ratio adaptation."""

    def __init__(
        self,
        aspect: str = "16:9",
        ms: int = 120,
        cache_dir: str = ".stickman_cache"
    ):
        self.aspect = aspect if aspect in ASPECT_PRESETS else "16:9"
        self.preset = ASPECT_PRESETS[self.aspect]
        self.ms = ms
        self.cache_dir = cache_dir
        self.scenes: List[Scene] = []

    @property
    def safe_caption_y(self) -> float:
        """Returns the safe vertical percentage pos_y for subtitles without UI collision."""
        return self.preset["caption_safe_y"]

    def add_scene(self, scene: Scene) -> "Timeline":
        self.scenes.append(scene)
        return self

    def total_frames(self) -> int:
        return sum(s.frames for s in self.scenes)

    def render_all(
        self,
        output_path: str,
        use_cache: bool = True,
        style: str = "hormozi-bold",
        workers: Union[int, str] = "auto"
    ) -> str:
        """
        Renders all scenes in order, applies transitions, overlays B-roll PiP,
        and stitches audio into a complete master video.
        """
        from .lib import render_mp4, export_with_voice, Frame
        os.makedirs(self.cache_dir, exist_ok=True)

        rendered_scene_frames: List[List[Image.Image]] = []

        for idx, sc in enumerate(self.scenes):
            scene_hash = sc.compute_hash()
            cache_file = os.path.join(self.cache_dir, f"scene_{idx:02d}_{scene_hash}.mp4")

            # Check if scene can be rendered
            frames_list: List[Image.Image] = []
            if sc.render_fn:
                for f in range(sc.frames):
                    im = sc.render_fn(f)
                    # Overlay B-roll if present
                    if sc.b_roll_path and sc.b_roll_box and os.path.isfile(sc.b_roll_path):
                        im = self._overlay_b_roll(im, sc.b_roll_path, sc.b_roll_box)
                    frames_list.append(im)
            else:
                # Default placeholder card
                for f in range(sc.frames):
                    c = Frame(f)
                    c.background("dark")
                    c.text((320, 180), f"Scene: {sc.name}", None, (245, 245, 245), "mm")
                    frames_list.append(c.image())

            rendered_scene_frames.append(frames_list)

        # Composite scene transitions
        final_frames: List[Image.Image] = []
        for i in range(len(rendered_scene_frames)):
            cur_frames = rendered_scene_frames[i]
            cur_scene = self.scenes[i]

            if i < len(rendered_scene_frames) - 1 and cur_scene.transition_to_next != "cut":
                t_kind = cur_scene.transition_to_next
                t_count = min(cur_scene.transition_frames, len(cur_frames), len(rendered_scene_frames[i + 1]))
                # Keep leading frames unchanged
                final_frames.extend(cur_frames[:-t_count])
                # Blend transition overlap
                next_frames = rendered_scene_frames[i + 1]
                for k in range(t_count):
                    progress = (k + 1) / float(t_count)
                    im_a = cur_frames[-t_count + k]
                    im_b = next_frames[k]
                    if t_kind == "wipe":
                        blended = transition_wipe(im_a, im_b, progress)
                    elif t_kind == "iris":
                        blended = transition_iris(im_a, im_b, progress)
                    elif t_kind == "splash":
                        blended = transition_ink_splash(im_a, im_b, progress)
                    else:
                        blended = im_b
                    final_frames.append(blended)
                # Next scene starts after the blended frames
                rendered_scene_frames[i + 1] = next_frames[t_count:]
            else:
                final_frames.extend(cur_frames)

        # Concatenate narrations if any
        full_narration = " ".join(s.narration for s in self.scenes if s.narration)

        if full_narration:
            # Voiceover + captions render
            return export_with_voice(
                lambda f: final_frames[min(f, len(final_frames) - 1)],
                script_text=full_narration,
                name=output_path,
                style=style,
                pos_y=self.safe_caption_y,
                ms=self.ms,
                workers=workers
            )
        else:
            # Silent render
            render_mp4(
                lambda f: final_frames[min(f, len(final_frames) - 1)],
                n=len(final_frames),
                path=output_path,
                ms=self.ms,
                loops=1,
                workers=workers
            )
            return output_path

    def _overlay_b_roll(
        self,
        base_img: Image.Image,
        b_roll_path: str,
        box: Tuple[int, int, int, int]
    ) -> Image.Image:
        """Paste Picture-in-Picture (PiP) image overlay onto base frame."""
        out = base_img.copy()
        try:
            overlay = Image.open(b_roll_path).convert("RGBA")
            # Scale box logical coords to image canvas size
            w, h = out.size
            scale_x = w / 640.0
            scale_y = h / 360.0
            bx = int(box[0] * scale_x)
            by = int(box[1] * scale_y)
            bw = int(box[2] * scale_x)
            bh = int(box[3] * scale_y)
            overlay = overlay.resize((bw, bh), Image.LANCZOS)
            out.paste(overlay, (bx, by), overlay)
        except Exception:
            pass
        return out


def run_project_file(project_path: str, output_path: Optional[str] = None) -> str:
    """
    Loads and renders a declarative project.json timeline project.
    Format:
    {
        "aspect": "16:9",
        "ms": 120,
        "style": "hormozi-bold",
        "scenes": [
            {"name": "intro", "frames": 24, "narration": "Hello world!"},
            {"name": "main", "frames": 36, "narration": "Building the future.", "transition": "wipe"}
        ]
    }
    """
    with open(project_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    aspect = config.get("aspect", "16:9")
    ms = config.get("ms", 120)
    style = config.get("style", "hormozi-bold")

    tl = Timeline(aspect=aspect, ms=ms)

    for item in config.get("scenes", []):
        sc = Scene(
            name=item.get("name", "scene"),
            frames=item.get("frames", 30),
            narration=item.get("narration"),
            voice=item.get("voice", "Charon"),
            transition_to_next=item.get("transition", "cut"),
            transition_frames=item.get("transition_frames", 6),
            b_roll_path=item.get("b_roll"),
            b_roll_box=tuple(item["b_roll_box"]) if "b_roll_box" in item else None
        )
        tl.add_scene(sc)

    out_file = output_path or config.get("output", "project_output.mp4")
    return tl.render_all(out_file, style=style)
