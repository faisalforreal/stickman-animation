"""Self-QA Bounding-Box Linter, Overlap Detector, and Searchable Asset Index.

Provides:
- Automated QA linting for storyboards and scenes:
  1. Off-canvas element detection.
  2. Element-on-element collision detection.
  3. Caption safe-zone collision check (ensures stage elements don't collide with subtitles).
  4. Narration length vs scene duration pacing check.
- Searchable asset index for LLM agents to find icons, poses, and styles by keyword.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from .presets import CURATED_PRESETS
from .icons import OFFLINE_ICONS


@dataclass
class QAIssue:
    severity: str  # "error", "warning", "info"
    code: str      # e.g. "OFF_CANVAS", "OVERLAP", "CAPTION_COLLISION", "PACING"
    message: str
    element_type: Optional[str] = None
    fix_suggestion: Optional[str] = None


@dataclass
class QAReport:
    passed: bool
    issues: List[QAIssue] = field(default_factory=list)

    def summary(self) -> str:
        if self.passed:
            return "QA Lint Passed: No critical issues found."
        lines = [f"QA Lint Failed: {len(self.issues)} issue(s) detected:"]
        for iss in self.issues:
            lines.append(f"  [{iss.severity.upper()}] {iss.code}: {iss.message}")
            if iss.fix_suggestion:
                lines.append(f"     Suggestion: {iss.fix_suggestion}")
        return "\n".join(lines)


def _boxes_intersect(b1: Tuple[float, float, float, float], b2: Tuple[float, float, float, float]) -> bool:
    """Returns True if box1 (x, y, w, h) intersects box2 (x, y, w, h)."""
    x1, y1, w1, h1 = b1
    x2, y2, w2, h2 = b2
    return not (x1 + w1 <= x2 or x2 + w2 <= x1 or y1 + h1 <= y2 or y2 + h2 <= y1)


def lint_storyboard(storyboard_dict: Dict[str, Any]) -> QAReport:
    """
    Analyzes a storyboard JSON/dict and flags off-canvas text, overlaps,
    caption collisions, and audio-scene pacing mismatches.
    """
    issues: List[QAIssue] = []
    aspect = storyboard_dict.get("aspect", "16:9")
    max_w = 360.0 if aspect == "9:16" else 640.0
    max_h = 640.0 if aspect == "9:16" else 360.0

    # Caption safe boundary (anything below this Y risks colliding with subtitles)
    caption_pct = 64.0 if aspect == "9:16" else 75.0
    caption_y_limit = max_h * (caption_pct / 100.0) - 25.0

    scenes = storyboard_dict.get("scenes", [])
    if not scenes:
        issues.append(QAIssue(
            severity="error",
            code="EMPTY_STORYBOARD",
            message="Storyboard contains no scenes.",
            fix_suggestion="Add at least one scene to the storyboard."
        ))

    for sc_idx, sc in enumerate(scenes):
        sc_name = sc.get("name", f"scene_{sc_idx}")
        frames = sc.get("frames", 30)
        narration = sc.get("narration", "")

        # 1. Pacing check: speaking speed should not exceed ~3.2 words per second
        if narration:
            word_count = len(narration.split())
            duration_sec = (frames * 120.0) / 1000.0
            max_words_fit = duration_sec * 3.5
            if word_count > max_words_fit:
                issues.append(QAIssue(
                    severity="warning",
                    code="PACING_TOO_FAST",
                    message=f"Scene '{sc_name}': narration ({word_count} words) may be too fast for {duration_sec:.1f}s.",
                    fix_suggestion=f"Increase scene frames from {frames} to {int(word_count / 3.0 * (1000.0 / 120.0))}."
                ))

        # 2. Elements checks
        placed_boxes: List[Tuple[str, Tuple[float, float, float, float]]] = []

        for el in sc.get("elements", []):
            el_type = el.get("type", "unknown")
            box = None

            if "box" in el:
                b = el["box"]
                box = (float(b[0]), float(b[1]), float(b[2]), float(b[3]))
            elif "pos" in el:
                pos = el["pos"]
                size = float(el.get("size", 30.0))
                box = (float(pos[0]) - size / 2.0, float(pos[1]) - size / 2.0, size, size)

            if box:
                bx, by, bw, bh = box
                # Off-canvas bounds check
                if bx < 0 or by < 0 or (bx + bw) > (max_w + 5) or (by + bh) > (max_h + 5):
                    issues.append(QAIssue(
                        severity="error",
                        code="OFF_CANVAS",
                        message=f"Scene '{sc_name}': {el_type} at ({bx:.0f}, {by:.0f}, {bw:.0f}, {bh:.0f}) extends outside canvas boundaries.",
                        element_type=el_type,
                        fix_suggestion="Adjust coordinates or scale to fit within canvas."
                    ))

                # Caption collision check
                if (by + bh) > caption_y_limit and narration:
                    issues.append(QAIssue(
                        severity="warning",
                        code="CAPTION_COLLISION",
                        message=f"Scene '{sc_name}': {el_type} at Y={by + bh:.0f} collides with caption subtitles (safe Y < {caption_y_limit:.0f}).",
                        element_type=el_type,
                        fix_suggestion="Move element upward or place captions at a different position."
                    ))

                # Overlap check against previously placed major UI elements
                if el_type in ("mockup", "chart", "mermaid"):
                    for prev_type, prev_box in placed_boxes:
                        if prev_type in ("mockup", "chart", "mermaid") and _boxes_intersect(box, prev_box):
                            issues.append(QAIssue(
                                severity="warning",
                                code="ELEMENT_OVERLAP",
                                message=f"Scene '{sc_name}': {el_type} overlaps with adjacent {prev_type}.",
                                element_type=el_type,
                                fix_suggestion="Separate elements side-by-side or place them in sequential scenes."
                            ))

                placed_boxes.append((el_type, box))

    has_errors = any(i.severity == "error" for i in issues)
    return QAReport(passed=not has_errors, issues=issues)


# ------------------------------------------------------------------ Searchable Asset Index
NAMED_POSES = [
    "walk", "run", "wave", "point", "type", "sit", "shrug",
    "jump", "celebrate", "fail", "hold", "hand_off", "think"
]

CHARACTER_ARCHETYPES = ["human", "robot", "server_bot"]
BACKGROUND_STYLES = ["dark", "light", "notebook", "blueprint", "chalkboard", "sepia", "grid"]
ACCESSORIES = ["hat", "crown", "headphones", "glasses", "tie"]


def search_assets(query: str) -> Dict[str, List[str]]:
    """
    Search the library for icons, poses, styles, and character accessories by keyword.
    Returns matched asset lists categorized by type.
    """
    q = query.lower().strip()
    results: Dict[str, List[str]] = {
        "icons": [],
        "poses": [],
        "archetypes": [],
        "backgrounds": [],
        "caption_styles": [],
        "accessories": []
    }

    # Match icons
    for icon_name in OFFLINE_ICONS.keys():
        if q in icon_name or any(part in icon_name for part in q.split()):
            results["icons"].append(icon_name)

    # Match poses
    for pose in NAMED_POSES:
        if q in pose:
            results["poses"].append(pose)

    # Match archetypes
    for arch in CHARACTER_ARCHETYPES:
        if q in arch:
            results["archetypes"].append(arch)

    # Match backgrounds
    for bg in BACKGROUND_STYLES:
        if q in bg:
            results["backgrounds"].append(bg)

    # Match caption presets
    for preset_name in CURATED_PRESETS.keys():
        if q in preset_name:
            results["caption_styles"].append(preset_name)

    # Match accessories
    for acc in ACCESSORIES:
        if q in acc:
            results["accessories"].append(acc)

    # Prune empty categories
    return {k: v for k, v in results.items() if v}
