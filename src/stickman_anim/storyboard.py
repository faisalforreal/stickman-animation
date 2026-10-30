"""Declarative Storyboard Runner for stickman_anim.

Allows LLM agents and creators to define entire animations declaratively
as clean JSON/dict specifications, lint them with Self-QA, and render them
straight to video with voice, lip-sync, and styled captions.
"""

import json
import os
from typing import Dict, Any, Optional, List, Tuple
from PIL import Image

from .timeline import Timeline, Scene
from .qa import lint_storyboard, QAReport


def _get_lib():
    from . import lib
    return lib


def _render_declarative_element(c: Any, el: Dict[str, Any], f: int, total_f: int) -> None:
    """Draw a single declarative element onto the Frame."""
    lib = _get_lib()
    el_type = el.get("type", "").lower()
    t = float(f)
    progress = min(1.0, max(0.0, f / float(max(1, total_f - 1))))

    if el_type == "character":
        cx = el.get("cx", 320.0)
        fl = el.get("floor_y", 310.0)
        kind = el.get("kind", "human")
        action = el.get("action", "idle")
        scale = el.get("scale", 1.0)
        accessories = el.get("accessories")
        props = el.get("props")
        mouth_open = el.get("mouth_open", 0.0)
        c.character(
            cx, fl,
            kind=kind,
            scale=scale,
            action=action,
            t=t,
            accessories=accessories,
            props=props,
            mouth_open=mouth_open
        )

    elif el_type == "icon":
        name = el.get("name", "sparkles")
        pos = el.get("pos", [320, 180])
        size = el.get("size", 36)
        col = tuple(el.get("col", [245, 245, 245]))
        draw_on = el.get("draw_on", progress)
        c.icon(name, (pos[0], pos[1]), size=size, col=col, draw_on=draw_on)

    elif el_type == "text":
        pos = el.get("pos", [320, 40])
        text_str = el.get("text", "")
        size = el.get("size", 18)
        col = tuple(el.get("col", [245, 245, 245]))
        anchor = el.get("anchor", "mm")
        c.text((pos[0], pos[1]), text_str, lib.font(size), col=col, anchor=anchor)

    elif el_type == "latex":
        expr = el.get("expr", r"E = mc^2")
        pos = el.get("pos", [320, 100])
        size = el.get("size", 24)
        c.latex(expr, (pos[0], pos[1]), size=size)

    elif el_type == "mermaid":
        code = el.get("code", "graph LR\nA --> B")
        box = tuple(el.get("box", [100, 100, 440, 160]))
        c.mermaid(code, box, draw_on=progress)

    elif el_type == "chart":
        chart_kind = el.get("chart_type", "bar")
        box = tuple(el.get("box", [100, 100, 240, 120]))
        data = el.get("data", [("A", 10), ("B", 20)])
        title = el.get("title", "")
        if chart_kind == "bar":
            c.chart_bar(box, data, title=title, progress=progress)
        elif chart_kind == "line":
            c.chart_line(box, data, title=title, progress=progress)

    elif el_type == "mockup":
        mock_kind = el.get("mockup_type", "browser")
        box = tuple(el.get("box", [60, 60, 520, 220]))
        if mock_kind == "browser":
            c.mockup_browser(box, url=el.get("url", "https://antigravity.dev"), progress=progress)
        elif mock_kind == "terminal":
            c.mockup_terminal(box, progress=progress)
        elif mock_kind == "phone":
            c.mockup_phone(box, progress=progress)

    elif el_type == "speech_bubble":
        speaker = tuple(el.get("speaker_pos", [320, 220]))
        text_str = el.get("text", "")
        thought = el.get("thought", False)
        c.speech_bubble(speaker, text_str, thought=thought, progress=1.0)

    elif el_type == "emote":
        pos = tuple(el.get("pos", [320, 200]))
        kind = el.get("kind", "!")
        c.emote(pos, kind=kind)

    elif el_type == "particles":
        ptype = el.get("particle_type", "confetti")
        origin = tuple(el.get("origin", [320, 180]))
        count = el.get("count", 20)
        if ptype == "confetti":
            c.confetti(origin, t=t * 0.1, count=count)
        elif ptype == "sparks":
            c.sparks(origin, t=t * 0.1, count=count)
        elif ptype == "smoke":
            c.smoke(origin, t=t * 0.1, count=count)


def build_storyboard_timeline(spec: Dict[str, Any]) -> Timeline:
    """Compiles a storyboard dictionary into a fully wired Timeline."""
    aspect = spec.get("aspect", "16:9")
    ms = spec.get("ms", 120)
    tl = Timeline(aspect=aspect, ms=ms)

    for sc_data in spec.get("scenes", []):
        sc_name = sc_data.get("name", "scene")
        sc_frames = sc_data.get("frames", 30)
        sc_narration = sc_data.get("narration")
        sc_voice = sc_data.get("voice", spec.get("voice", "Charon"))
        sc_trans = sc_data.get("transition", "cut")
        sc_bg = sc_data.get("background", "dark")
        sc_floor = sc_data.get("floor_y", 310.0)
        elements = sc_data.get("elements", [])

        # Factory to bind scene variables into render closure
        def make_render(bg_style, floor_val, els, n_f):
            def render_fn(f):
                c = _get_lib().Frame(f)
                c.background(bg_style)
                if floor_val:
                    c.floor(floor_val)
                for el in els:
                    _render_declarative_element(c, el, f, n_f)
                return c.image()
            return render_fn

        scene_obj = Scene(
            name=sc_name,
            render_fn=make_render(sc_bg, sc_floor, elements, sc_frames),
            frames=sc_frames,
            narration=sc_narration,
            voice=sc_voice,
            transition_to_next=sc_trans
        )
        tl.add_scene(scene_obj)

    return tl


def render_storyboard(
    spec_or_path: Any,
    output_path: str = "storyboard_output.mp4",
    lint: bool = True
) -> str:
    """
    Main entry point: loads storyboard JSON or dict, lints layout,
    and renders output video.
    """
    if isinstance(spec_or_path, str) and os.path.isfile(spec_or_path):
        with open(spec_or_path, "r", encoding="utf-8") as f:
            spec = json.load(f)
    elif isinstance(spec_or_path, dict):
        spec = spec_or_path
    else:
        raise ValueError("spec_or_path must be a dictionary or JSON file path.")

    if lint:
        report = lint_storyboard(spec)
        print(report.summary())
        if not report.passed:
            raise RuntimeError(f"Storyboard failed QA linting:\n{report.summary()}")

    timeline = build_storyboard_timeline(spec)
    style = spec.get("style", "hormozi-bold")
    return timeline.render_all(output_path, style=style)
