"""Style presets and configuration for video subtitles in stickman_anim.

Integrates curated viral styles and 400+ CapCut-compatible presets
from AutoCaptions and AutoCaptionsWeb.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import json
import os


def rgb_to_hex(r: int, g: int, b: int) -> str:
    """Convert RGB integers to hex string (#RRGGBB)."""
    return f"#{max(0, min(255, int(r))):02X}{max(0, min(255, int(g))):02X}{max(0, min(255, int(b))):02X}"


def hex_to_ass_color(hex_str: str, opacity: float = 1.0) -> str:
    """
    Convert a hex color string (#RRGGBB) to ASS color format (&HAABBGGRR&).
    In ASS: Alpha 00 is fully opaque, FF is fully transparent; color order is BGR.
    """
    cleaned = hex_str.strip().lstrip("#").upper()
    if len(cleaned) == 3:
        cleaned = "".join(c * 2 for c in cleaned)
    if len(cleaned) != 6:
        cleaned = "FFFFFF"

    r = int(cleaned[0:2], 16)
    g = int(cleaned[2:4], 16)
    b = int(cleaned[4:6], 16)

    clamped_opacity = max(0.0, min(1.0, opacity))
    alpha = int(round((1.0 - clamped_opacity) * 255))
    return f"&H{alpha:02X}{b:02X}{g:02X}{r:02X}&"


@dataclass
class CaptionStyle:
    """Unified subtitle style definition."""
    name: str = "custom"
    font_name: str = "Arial Black"
    font_size: int = 40
    primary_color: str = "#FFFFFF"       # Base text color
    highlight_color: str = "#FFE600"     # Active spoken word highlight
    secondary_color: str = "#00FF66"
    stroke_color: str = "#000000"
    stroke_width: float = 3.0
    shadow_color: str = "#000000"
    shadow_depth: float = 1.5
    
    # Background Box / Pill Badge
    has_box: bool = False
    box_rounded: bool = True
    box_radius: int = 14
    box_padding_x: int = 24
    box_padding_y: int = 12
    box_border_width: float = 1.5
    box_border_color: str = "#2A2A2A"
    box_color: str = "#121212"
    box_opacity: float = 0.90
    
    # Typography & Case
    all_caps: bool = True
    bold: bool = True
    italic: bool = False
    
    # Position: Default 75.0% distance from top (25% from bottom)
    pos_y: float = 75.0
    words_per_chunk: int = 3
    
    # Effect / Animation mode
    effect_type: str = "POP"             # 'POP', 'SPRING_BOUNCE', 'GLOW', 'KARAOKE_WIPE', 'FADE', 'NONE'
    display_mode: str = "LINE"           # 'LINE' or 'WORD'


# Curated viral preset definitions
CURATED_PRESETS: Dict[str, CaptionStyle] = {
    # 1. Hormozi Bold: Massive bold uppercase with energetic yellow active-word highlight
    "hormozi-bold": CaptionStyle(
        name="hormozi-bold",
        font_name="Arial Black",
        font_size=46,
        primary_color="#FFFFFF",
        highlight_color="#FFE600",       # Vibrant Yellow
        stroke_color="#000000",
        stroke_width=3.6,
        shadow_depth=2.0,
        has_box=False,
        all_caps=True,
        bold=True,
        pos_y=75.0,
        words_per_chunk=3,
        effect_type="POP",
    ),

    # 2. MrBeast Explosive: Thick stroke, vibrant green highlight, high retention
    "mrbeast-pop": CaptionStyle(
        name="mrbeast-pop",
        font_name="Impact",
        font_size=48,
        primary_color="#FFFFFF",
        highlight_color="#2BF82A",       # Neon Beast Green
        stroke_color="#000000",
        stroke_width=4.0,
        shadow_depth=2.5,
        has_box=False,
        all_caps=True,
        bold=True,
        pos_y=72.0,
        words_per_chunk=2,
        effect_type="POP",
    ),

    # 3. Ali Abdaal Clean: Minimalist dark rounded pill badge with sky blue highlight
    "ali-abdaal-clean": CaptionStyle(
        name="ali-abdaal-clean",
        font_name="Segoe UI",
        font_size=36,
        primary_color="#F5F5F7",
        highlight_color="#38BDF8",       # Sky Blue
        stroke_color="#000000",
        stroke_width=0.0,
        shadow_depth=0.0,
        has_box=True,
        box_rounded=True,
        box_radius=16,
        box_padding_x=28,
        box_padding_y=14,
        box_color="#0F0F1A",
        box_opacity=0.85,
        all_caps=False,
        bold=True,
        pos_y=75.0,
        words_per_chunk=4,
        effect_type="FADE",
    ),

    # 4. Cyberpunk Neon: Electric cyan base with glowing neon pink active words
    "cyberpunk-neon": CaptionStyle(
        name="cyberpunk-neon",
        font_name="Arial Black",
        font_size=42,
        primary_color="#00F0FF",         # Electric Cyan
        highlight_color="#FF0080",       # Neon Pink
        stroke_color="#0A0A1E",
        stroke_width=3.0,
        shadow_depth=2.0,
        has_box=True,
        box_rounded=True,
        box_radius=10,
        box_padding_x=20,
        box_padding_y=10,
        box_color="#05050F",
        box_opacity=0.75,
        all_caps=True,
        bold=True,
        pos_y=75.0,
        words_per_chunk=3,
        effect_type="GLOW",
    ),

    # 5. Dev Code Pill: Monospace terminal style with emerald highlight
    "dev-minimal": CaptionStyle(
        name="dev-minimal",
        font_name="Consolas",
        font_size=34,
        primary_color="#DCDCE6",
        highlight_color="#10B981",       # Emerald Green
        stroke_color="#000000",
        stroke_width=0.0,
        shadow_depth=0.0,
        has_box=True,
        box_rounded=True,
        box_radius=12,
        box_padding_x=24,
        box_padding_y=12,
        box_color="#141423",
        box_opacity=0.92,
        all_caps=False,
        bold=True,
        pos_y=75.0,
        words_per_chunk=4,
        effect_type="POP",
    ),

    # 6. Karaoke Gold: Smooth horizontal gold wipe
    "karaoke-gold": CaptionStyle(
        name="karaoke-gold",
        font_name="Arial Black",
        font_size=42,
        primary_color="#8C8C9B",         # Dim grey inactive
        highlight_color="#FFD700",       # Gold
        stroke_color="#000000",
        stroke_width=2.5,
        shadow_depth=1.5,
        has_box=False,
        all_caps=True,
        bold=True,
        pos_y=75.0,
        words_per_chunk=4,
        effect_type="KARAOKE_WIPE",
    ),

    # 7. Luxury Editorial: Elegant serif typography with champagne gold
    "luxury-editorial": CaptionStyle(
        name="luxury-editorial",
        font_name="Georgia",
        font_size=38,
        primary_color="#F5F5F0",
        highlight_color="#D4AF37",       # Champagne Gold
        stroke_color="#000000",
        stroke_width=1.0,
        shadow_depth=1.0,
        has_box=False,
        all_caps=False,
        bold=False,
        italic=True,
        pos_y=75.0,
        words_per_chunk=4,
        effect_type="FADE",
    ),

    # 8. Bold Red Accent (AutoCaptions default)
    "bold_red_accent": CaptionStyle(
        name="bold_red_accent",
        font_name="Arial Black",
        font_size=42,
        primary_color="#FFFFFF",
        highlight_color="#FF2020",       # Crimson Red
        stroke_color="#000000",
        stroke_width=3.2,
        shadow_depth=1.8,
        has_box=False,
        all_caps=True,
        bold=True,
        pos_y=75.0,
        words_per_chunk=3,
        effect_type="POP",
    ),

    # 9. Bold Green Accent
    "bold_green_accent": CaptionStyle(
        name="bold_green_accent",
        font_name="Arial Black",
        font_size=42,
        primary_color="#FFFFFF",
        highlight_color="#00FF66",       # Shiny Neon Green
        stroke_color="#000000",
        stroke_width=3.2,
        shadow_depth=1.8,
        has_box=False,
        all_caps=True,
        bold=True,
        pos_y=75.0,
        words_per_chunk=3,
        effect_type="POP",
    ),

    # 10. Boxed Red Accent
    "boxed_red_accent": CaptionStyle(
        name="boxed_red_accent",
        font_name="Arial Black",
        font_size=34,
        primary_color="#FFFFFF",
        highlight_color="#FF2020",
        stroke_color="#000000",
        stroke_width=0.5,
        shadow_depth=0.0,
        has_box=True,
        box_rounded=True,
        box_radius=20,
        box_padding_x=36,
        box_padding_y=18,
        box_color="#121212",
        box_opacity=0.90,
        all_caps=True,
        bold=True,
        pos_y=75.0,
        words_per_chunk=3,
        effect_type="POP",
    ),

    # 11. Boxed Green Accent
    "boxed_green_accent": CaptionStyle(
        name="boxed_green_accent",
        font_name="Arial Black",
        font_size=34,
        primary_color="#FFFFFF",
        highlight_color="#00FF66",
        stroke_color="#000000",
        stroke_width=0.5,
        shadow_depth=0.0,
        has_box=True,
        box_rounded=True,
        box_radius=20,
        box_padding_x=36,
        box_padding_y=18,
        box_color="#121212",
        box_opacity=0.90,
        all_caps=True,
        bold=True,
        pos_y=75.0,
        words_per_chunk=3,
        effect_type="POP",
    ),
}

# Cache for extended CapCut presets
_CAPCUT_PRESETS_CACHE: Optional[Dict[str, Dict[str, Any]]] = None


def _load_capcut_raw_presets() -> Dict[str, Dict[str, Any]]:
    """Load the raw 406 CapCut presets JSON file."""
    global _CAPCUT_PRESETS_CACHE
    if _CAPCUT_PRESETS_CACHE is not None:
        return _CAPCUT_PRESETS_CACHE

    _CAPCUT_PRESETS_CACHE = {}
    json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "capcut_presets.json")
    if os.path.isfile(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    for item in data:
                        pid = item.get("id") or item.get("name", "").lower().replace(" ", "-")
                        if pid:
                            _CAPCUT_PRESETS_CACHE[pid] = item
                            # Also map name
                            name_key = item.get("name", "").lower().replace(" ", "-")
                            if name_key:
                                _CAPCUT_PRESETS_CACHE[name_key] = item
        except Exception as e:
            print(f"[stickman_anim.presets] Warning: Failed to load capcut_presets.json: {e}")

    return _CAPCUT_PRESETS_CACHE


def _capcut_to_caption_style(data: Dict[str, Any]) -> CaptionStyle:
    """Convert a raw CapCut preset dictionary into CaptionStyle."""
    name = data.get("name", "capcut-preset")
    font_info = data.get("font", {})
    font_name = font_info.get("name", "Arial Black")
    
    colors = data.get("colors", {})
    def_colors = colors.get("defaultColor", [{}])
    spoken_colors = colors.get("spokenColor", [{}])
    stroke_colors = colors.get("strokeColor", [{}])
    bg_colors = colors.get("backgroundColor", [{}])
    shadow_colors = colors.get("shadowColor", [{}])

    primary_hex = rgb_to_hex(def_colors[0].get("r", 255), def_colors[0].get("g", 255), def_colors[0].get("b", 255)) if def_colors else "#FFFFFF"
    spoken_hex = rgb_to_hex(spoken_colors[0].get("r", 255), spoken_colors[0].get("g", 230), spoken_colors[0].get("b", 0)) if spoken_colors else "#FFE600"
    stroke_hex = rgb_to_hex(stroke_colors[0].get("r", 0), stroke_colors[0].get("g", 0), stroke_colors[0].get("b", 0)) if stroke_colors else "#000000"
    
    bg_alpha = bg_colors[0].get("a", 0.0) if bg_colors else 0.0
    bg_hex = rgb_to_hex(bg_colors[0].get("r", 0), bg_colors[0].get("g", 0), bg_colors[0].get("b", 0)) if bg_colors else "#000000"
    shadow_hex = rgb_to_hex(shadow_colors[0].get("r", 0), shadow_colors[0].get("g", 0), shadow_colors[0].get("b", 0)) if shadow_colors else "#000000"

    sizes = data.get("sizes", {})
    font_size = sizes.get("fontSize", 42)
    stroke_width = max(0.0, float(sizes.get("strokeSize", 6)) / 3.0)
    shadow_depth = max(0.0, float(sizes.get("blurSize", 4)) / 3.0)

    has_box = data.get("wordHasBackground", False) or bg_alpha > 0.05
    box_radius = sizes.get("backgroundRadius", 12)
    box_pad_x = sizes.get("backgroundPaddingX", 20)
    box_pad_y = sizes.get("backgroundPaddingY", 10)
    
    pos_y = float(sizes.get("posY", 75.0))
    all_caps = data.get("capitalizationType", "DEFAULT").upper() == "UPPERCASE"
    
    modes = data.get("modes", {})
    effect_type = modes.get("effectType", "POP")
    display_mode = modes.get("displayMode", "LINE")
    words_per_chunk = data.get("wordsPerLineCount", 3)

    return CaptionStyle(
        name=name,
        font_name=font_name,
        font_size=font_size,
        primary_color=primary_hex,
        highlight_color=spoken_hex,
        stroke_color=stroke_hex,
        stroke_width=stroke_width,
        shadow_color=shadow_hex,
        shadow_depth=shadow_depth,
        has_box=has_box,
        box_rounded=True,
        box_radius=box_radius,
        box_padding_x=box_pad_x,
        box_padding_y=box_pad_y,
        box_color=bg_hex,
        box_opacity=float(bg_alpha) if bg_alpha > 0 else 0.85,
        all_caps=all_caps,
        bold=True,
        pos_y=pos_y,
        words_per_chunk=max(1, words_per_chunk),
        effect_type=effect_type,
        display_mode=display_mode,
    )


def get_preset(name_or_id: str) -> CaptionStyle:
    """
    Look up a preset by name or ID.
    Checks curated presets first, then extended 400+ CapCut library.
    Defaults to 'hormozi-bold' if not found.
    """
    cleaned = name_or_id.strip().lower().replace("_", "-")

    if cleaned in CURATED_PRESETS:
        return CURATED_PRESETS[cleaned]
    # Check with original underscores
    under = cleaned.replace("-", "_")
    if under in CURATED_PRESETS:
        return CURATED_PRESETS[under]

    # Search extended CapCut library
    capcut_map = _load_capcut_raw_presets()
    if cleaned in capcut_map:
        return _capcut_to_caption_style(capcut_map[cleaned])

    # Partial match
    for k, v in capcut_map.items():
        if cleaned in k:
            return _capcut_to_caption_style(v)

    print(f"[stickman_anim.presets] Preset '{name_or_id}' not found. Defaulting to 'hormozi-bold'.")
    return CURATED_PRESETS["hormozi-bold"]


def list_presets(search: Optional[str] = None, category: Optional[str] = None) -> List[Dict[str, Any]]:
    """List available presets with descriptions and categories."""
    results = []

    for k, s in CURATED_PRESETS.items():
        results.append({
            "id": k,
            "name": s.name,
            "category": "curated",
            "highlight_color": s.highlight_color,
            "has_box": s.has_box,
            "effect_type": s.effect_type,
            "pos_y": s.pos_y,
        })

    capcut_map = _load_capcut_raw_presets()
    seen = set(CURATED_PRESETS.keys())
    for k, raw in capcut_map.items():
        pid = raw.get("id", k)
        if pid in seen:
            continue
        seen.add(pid)
        cat = raw.get("category", "general")
        results.append({
            "id": pid,
            "name": raw.get("name", pid),
            "category": cat,
            "highlight_color": rgb_to_hex(raw.get("colors", {}).get("spokenColor", [{}])[0].get("r", 255),
                                          raw.get("colors", {}).get("spokenColor", [{}])[0].get("g", 230),
                                          raw.get("colors", {}).get("spokenColor", [{}])[0].get("b", 0)),
            "has_box": raw.get("wordHasBackground", False),
            "effect_type": raw.get("modes", {}).get("effectType", "POP"),
            "pos_y": float(raw.get("sizes", {}).get("posY", 75.0)),
        })

    if category:
        results = [r for r in results if r.get("category", "").lower() == category.lower()]
    if search:
        q = search.lower()
        results = [r for r in results if q in r.get("id", "").lower() or q in r.get("name", "").lower()]

    return results
