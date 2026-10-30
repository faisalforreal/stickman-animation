"""Advanced Exporters: Social Presets, Transparent Video, Animated SVG, and Auto-Thumbnails.

Provides:
- Social platform export presets (YouTube, Shorts, Reels, X, LinkedIn).
- Transparent background video export (WebM VP9 alpha & ProRes 4444 MOV).
- Self-contained Animated SVG exporter using CSS stroke-dashoffset animations.
- Intelligent Auto-Thumbnail generator that detects peak visual engagement frames.
"""

import math
import os
import shutil
import subprocess
import tempfile
from typing import List, Dict, Any, Optional, Tuple
from PIL import Image, ImageStat
from .paths import Path


# ------------------------------------------------------------------ 1. Social Export Presets
SOCIAL_PRESETS: Dict[str, Dict[str, Any]] = {
    "youtube": {
        "size": (1920, 1080),
        "fps": 30,
        "crf": 18,
        "aspect": "16:9",
        "container": "mp4",
        "vcodec": "libx264",
        "pix_fmt": "yuv420p"
    },
    "shorts": {
        "size": (1080, 1920),
        "fps": 30,
        "crf": 18,
        "aspect": "9:16",
        "container": "mp4",
        "vcodec": "libx264",
        "pix_fmt": "yuv420p"
    },
    "reels": {
        "size": (1080, 1920),
        "fps": 30,
        "crf": 19,
        "aspect": "9:16",
        "container": "mp4",
        "vcodec": "libx264",
        "pix_fmt": "yuv420p"
    },
    "x": {
        "size": (1280, 720),
        "fps": 30,
        "crf": 20,
        "aspect": "16:9",
        "container": "mp4",
        "vcodec": "libx264",
        "pix_fmt": "yuv420p"
    },
    "linkedin": {
        "size": (1080, 1080),
        "fps": 30,
        "crf": 19,
        "aspect": "1:1",
        "container": "mp4",
        "vcodec": "libx264",
        "pix_fmt": "yuv420p"
    }
}


def export_social(
    input_video: str,
    output_path: str,
    platform: str = "youtube"
) -> str:
    """Re-encodes a video to platform-optimized resolutions and bitrate targets."""
    plat = platform.lower().strip()
    if plat not in SOCIAL_PRESETS:
        plat = "youtube"
    spec = SOCIAL_PRESETS[plat]
    w, h = spec["size"]

    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", input_video,
        "-vf", f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,fps={spec['fps']}",
        "-c:v", spec["vcodec"],
        "-preset", "slow",
        "-crf", str(spec["crf"]),
        "-pix_fmt", spec["pix_fmt"],
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        output_path
    ]
    subprocess.run(cmd, check=True)
    return output_path


def export_transparent_video(
    frames: List[Image.Image],
    output_path: str,
    fps: int = 24,
    format_type: str = "webm"  # "webm" or "prores"
) -> str:
    """
    Exports animation with transparent background.
    - WebM uses VP9 with yuva420p (perfect for web overlay / OBS / HTML5).
    - MOV uses Apple ProRes 4444 with alpha (ideal for editing in Premiere/FinalCut).
    """
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg required for transparent video export")

    first = frames[0]
    w, h = first.size
    w2, h2 = w - w % 2, h - h % 2

    if format_type == "prores" or output_path.endswith(".mov"):
        cmd = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{w}x{h}",
            "-framerate", str(fps), "-i", "-",
            "-vf", f"crop={w2}:{h2}:0:0",
            "-c:v", "prores_ks", "-profile:v", "4",
            "-pix_fmt", "yuva444p10le",
            output_path
        ]
    else:
        # Default WebM VP9 with alpha
        cmd = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{w}x{h}",
            "-framerate", str(fps), "-i", "-",
            "-vf", f"crop={w2}:{h2}:0:0",
            "-c:v", "libvpx-vp9", "-b:v", "2M",
            "-pix_fmt", "yuva420p",
            output_path
        ]

    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for im in frames:
        p.stdin.write(im.convert("RGBA").tobytes())
    p.stdin.close()
    if p.wait() != 0:
        raise RuntimeError(f"FFmpeg failed while writing transparent video: {output_path}")

    return output_path


# ------------------------------------------------------------------ 2. Animated SVG Exporter
def export_animated_svg(
    paths: List[Path],
    output_path: str,
    width: int = 640,
    height: int = 360,
    duration_sec: float = 3.0,
    stroke_color: str = "#f5f5f5",
    stroke_width: float = 2.4,
    bg_color: str = "#000000"
) -> str:
    """
    Exports vector Paths into a self-contained Animated SVG.
    Uses CSS `@keyframes` and `stroke-dashoffset` for resolution-independent vector playback.
    """
    svg_elements = []
    total_paths = len(paths)

    css_rules = [
        f"@keyframes drawStroke {{ from {{ stroke-dashoffset: 1000; }} to {{ stroke-dashoffset: 0; }} }}",
        f".hand-path {{ stroke-dasharray: 1000; stroke-dashoffset: 1000; animation: drawStroke {duration_sec}s cubic-bezier(0.4, 0, 0.2, 1) forwards; fill: none; stroke: {stroke_color}; stroke-width: {stroke_width}; stroke-linecap: round; stroke-linejoin: round; }}"
    ]

    for idx, p in enumerate(paths):
        d_strs = []
        for poly in p.get_polylines():
            if not poly:
                continue
            d_parts = [f"M {poly[0][0]:.1f} {poly[0][1]:.1f}"]
            for pt in poly[1:]:
                d_parts.append(f"L {pt[0]:.1f} {pt[1]:.1f}")
            d_strs.append(" ".join(d_parts))

        d_attr = " ".join(d_strs)
        delay = (idx / float(max(1, total_paths))) * (duration_sec * 0.4)
        svg_elements.append(f'<path class="hand-path" style="animation-delay: {delay:.2f}s;" d="{d_attr}" />')

    svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="100%" height="100%" style="background-color: {bg_color};">
  <defs>
    <style>
      {' '.join(css_rules)}
    </style>
  </defs>
  {' '.join(svg_elements)}
</svg>"""

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(svg_content)
    return output_path


# ------------------------------------------------------------------ 3. Auto-Thumbnail Generator
def generate_thumbnail(
    frames_or_video: Any,
    output_path: str = "thumbnail.png",
    title_badge: Optional[str] = None
) -> str:
    """
    Selects the most visually engaging frame (highest edge variance / content complexity)
    from a sequence of frames or video file, and saves high-resolution thumbnail.
    """
    from PIL import ImageDraw, ImageFilter, ImageFont
    frames: List[Image.Image] = []

    if isinstance(frames_or_video, list):
        frames = frames_or_video
    elif isinstance(frames_or_video, str) and os.path.isfile(frames_or_video):
        # Extract sample frames from video file
        temp_dir = tempfile.mkdtemp()
        cmd = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", frames_or_video,
            "-vf", "fps=2",
            os.path.join(temp_dir, "thumb_%03d.png")
        ]
        try:
            subprocess.run(cmd, check=True)
            for fname in sorted(os.listdir(temp_dir)):
                if fname.endswith(".png"):
                    frames.append(Image.open(os.path.join(temp_dir, fname)).copy())
        except Exception:
            pass

    if not frames:
        # Fallback dummy frame
        frames = [Image.new("RGB", (1280, 720), (18, 18, 18))]

    # Score frames by edge complexity (avoids empty opening or blank closing cards)
    best_frame = frames[0]
    best_score = -1.0

    for im in frames:
        # Gray edge variance score
        gray = im.convert("L").filter(ImageFilter.FIND_EDGES)
        stat = ImageStat.Stat(gray)
        score = stat.var[0]
        if score > best_score:
            best_score = score
            best_frame = im

    thumb = best_frame.copy()

    # Optional Title Badge
    if title_badge:
        d = ImageDraw.Draw(thumb)
        fnt = ImageFont.load_default()
        bbox = d.textbbox((0, 0), title_badge, font=fnt)
        bw = (bbox[2] - bbox[0]) * 3 + 40
        bh = (bbox[3] - bbox[1]) * 3 + 24
        cx = thumb.width / 2.0
        cy = thumb.height - 80.0
        # Draw rounded badge
        d.rounded_rectangle([cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2], radius=12, fill=(18, 18, 22), outline=(80, 220, 255), width=3)
        d.text((cx, cy), title_badge, font=fnt, fill=(245, 245, 245), anchor="mm")

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    thumb.save(output_path, "PNG")
    return output_path
