"""Video captions engine for stickman_anim.

Features:
- Syllable/punctuation-weighted timing estimator (offline, zero external API required).
- Deepgram transcription with word timestamps (optional).
- ASS (Advanced SubStation Alpha) subtitle generator with:
  - Modern rounded badge boxes (Layer 0 vector graphics)
  - Active-word color highlights
  - Spring-bounce pop animations (\\t transforms)
  - Karaoke color wipes (\\kf tags)
  - Configurable vertical placement (default 75% distance from top)
- FFmpeg subtitle burning and audio muxing pipeline with safe Windows path escaping.
"""

import os
import re
import json
import subprocess
import tempfile
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont

from .presets import CaptionStyle, get_preset, hex_to_ass_color


@dataclass
class WordItem:
    word: str
    start: float
    end: float
    punctuated_word: str = ""
    is_keyword: bool = False

    def __post_init__(self):
        if not self.punctuated_word:
            self.punctuated_word = self.word


@dataclass
class ChunkItem:
    start: float
    end: float
    words: List[WordItem] = field(default_factory=list)

    @property
    def text(self) -> str:
        return " ".join(w.punctuated_word for w in self.words)


def format_ass_time(seconds: float) -> str:
    """Format seconds into ASS timestamp H:MM:SS.cs (centiseconds)."""
    seconds = max(0.0, float(seconds))
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centis = int(round((seconds - int(seconds)) * 100))
    if centis >= 100:
        centis = 99
    return f"{hours}:{minutes:02d}:{secs:02d}.{centis:02d}"


def escape_ffmpeg_ass_path(path: str) -> str:
    """
    Safely escape subtitle path for FFmpeg's libass filter on Windows and POSIX.
    Example on Windows: C:\\path\\sub.ass -> C\\:/path/sub.ass
    """
    normalized = os.path.abspath(path).replace("\\", "/")
    escaped = normalized.replace(":", r"\:").replace("'", r"\'")
    return escaped


def measure_text_dimensions(text: str, font_name: str, font_size: int) -> Tuple[int, int]:
    """Measure pixel width and height of text for ASS bounding box."""
    font = None
    lower = font_name.lower()
    candidates = [font_name]
    if "black" in lower:
        candidates.extend(["ariblk.ttf", "Arial Black.ttf", "arialbd.ttf"])
    elif "impact" in lower:
        candidates.extend(["impact.ttf", "Impact.ttf", "ariblk.ttf"])
    elif "consolas" in lower or "mono" in lower:
        candidates.extend(["consola.ttf", "courbd.ttf", "segoeui.ttf"])
    else:
        candidates.extend(["arial.ttf", "arialbd.ttf", "segoeui.ttf"])

    for cand in candidates:
        try:
            font = ImageFont.truetype(cand, font_size)
            break
        except Exception:
            continue

    if font is None:
        font = ImageFont.load_default()

    im = Image.new("RGB", (10, 10))
    draw = ImageDraw.Draw(im)
    bbox = draw.textbbox((0, 0), text, font=font)
    w = max(10, bbox[2] - bbox[0])
    h = max(10, bbox[3] - bbox[1])
    return w, h


def make_rounded_rect_path(w: float, h: float, r: float) -> str:
    """Generate ASS vector drawing commands (\\p1) for a rounded rectangle."""
    r = max(0.0, min(r, w / 2.0, h / 2.0))
    if r <= 0.0:
        return f"m 0 0 l {w:.1f} 0 l {w:.1f} {h:.1f} l 0 {h:.1f}"

    k = r * 0.55228475  # Bézier constant for quarter-circle
    return (
        f"m {r:.1f} 0 "
        f"l {w - r:.1f} 0 "
        f"b {w - r + k:.1f} 0 {w:.1f} {r - k:.1f} {w:.1f} {r:.1f} "
        f"l {w:.1f} {h - r:.1f} "
        f"b {w:.1f} {h - r + k:.1f} {w - r + k:.1f} {h:.1f} {w - r:.1f} {h:.1f} "
        f"l {r:.1f} {h:.1f} "
        f"b {r - k:.1f} {h:.1f} 0 {h - r + k:.1f} 0 {h - r:.1f} "
        f"l 0 {r:.1f} "
        f"b 0 {r - k:.1f} {r - k:.1f} 0 {r:.1f} 0"
    )


def estimate_word_timings(text: str, total_duration: float) -> List[WordItem]:
    """
    Syllable/character-weighted timing estimator.
    Accurately maps words to total audio duration with speech pause models.
    """
    tokens = text.strip().split()
    if not tokens:
        return []

    # Calculate word weights based on character length and punctuation
    weights = []
    for t in tokens:
        clean = re.sub(r"[^\w]", "", t)
        w = max(1, len(clean))
        # Extra pause after commas or sentence endings
        if t.endswith((",", ";", ":")):
            w += 1.5
        elif t.endswith((".", "!", "?")):
            w += 3.0
        weights.append(w)

    total_weight = sum(weights)
    lead_in = 0.15
    usable_duration = max(0.5, total_duration - lead_in - 0.2)

    words = []
    cursor = lead_in
    for i, t in enumerate(tokens):
        fraction = weights[i] / total_weight
        dur = max(0.20, fraction * usable_duration)
        clean = re.sub(r"[^\w]", "", t).upper()
        
        words.append(WordItem(
            word=clean,
            punctuated_word=t,
            start=round(cursor, 2),
            end=round(cursor + dur * 0.85, 2),
            is_keyword=bool(re.match(r"^(\d+|AI|PR|CI|CD|AUTOMATION|SUCCESS|ERROR|DONE|READY)", clean))
        ))
        cursor += dur

    return words


def transcribe_with_deepgram(audio_path: str, api_key: Optional[str] = None) -> List[WordItem]:
    """Send audio to Deepgram REST API for millisecond-precision word timestamps."""
    import requests

    key = api_key or os.getenv("DEEPGRAM_API_KEY")
    if not key:
        raise ValueError("DEEPGRAM_API_KEY is not set.")

    url = "https://api.deepgram.com/v1/listen?model=nova-2&smart_format=true&punctuate=true"
    headers = {
        "Authorization": f"Token {key}",
        "Content-Type": "audio/mp3",
    }

    with open(audio_path, "rb") as f:
        audio_data = f.read()

    resp = requests.post(url, headers=headers, data=audio_data, timeout=60)
    if resp.status_code != 200:
        raise RuntimeError(f"Deepgram API error ({resp.status_code}): {resp.text}")

    data = resp.json()
    channels = data.get("results", {}).get("channels", [])
    if not channels:
        return []

    raw_words = channels[0].get("alternatives", [{}])[0].get("words", [])
    result = []
    for rw in raw_words:
        result.append(WordItem(
            word=rw.get("word", ""),
            punctuated_word=rw.get("punctuated_word", rw.get("word", "")),
            start=float(rw.get("start", 0.0)),
            end=float(rw.get("end", 0.0)),
        ))
    return result


def get_word_timings(
    audio_path: str,
    script_text: Optional[str] = None,
    api_key: Optional[str] = None,
    duration: Optional[float] = None,
) -> List[WordItem]:
    """
    Get word timestamps. Uses Deepgram if API key is provided,
    otherwise smoothly estimates timings based on syllable rhythm.
    """
    deepgram_key = api_key or os.getenv("DEEPGRAM_API_KEY")
    if deepgram_key:
        try:
            words = transcribe_with_deepgram(audio_path, deepgram_key)
            if words:
                return words
        except Exception as e:
            print(f"[stickman_anim.captions] Deepgram transcription notice: {e}. Falling back to timing estimator.")

    from .tts import get_audio_duration
    dur = duration or get_audio_duration(audio_path)
    text = script_text or "Stickman animated explainer video"
    return estimate_word_timings(text, dur)


def chunk_words(
    words: List[WordItem],
    max_words_per_chunk: int = 3,
    max_gap_seconds: float = 0.5,
) -> List[ChunkItem]:
    """Group words into punchy, high-retention subtitle bursts."""
    if not words:
        return []

    chunks: List[ChunkItem] = []
    current_words: List[WordItem] = [words[0]]

    for i in range(1, len(words)):
        prev_w = words[i - 1]
        curr_w = words[i]
        time_gap = curr_w.start - prev_w.end
        ends_sentence = prev_w.punctuated_word.endswith((".", "!", "?"))

        should_split = (
            len(current_words) >= max_words_per_chunk
            or time_gap > max_gap_seconds
            or ends_sentence
        )

        if should_split:
            chunks.append(ChunkItem(
                start=current_words[0].start,
                end=max(current_words[-1].end, current_words[0].start + 0.4),
                words=current_words
            ))
            current_words = [curr_w]
        else:
            current_words.append(curr_w)

    if current_words:
        chunks.append(ChunkItem(
            start=current_words[0].start,
            end=max(current_words[-1].end, current_words[0].start + 0.4),
            words=current_words
        ))

    return chunks


def build_ass_subtitles(
    chunks: List[ChunkItem],
    style: CaptionStyle,
    play_res_x: int = 1280,
    play_res_y: int = 720,
) -> str:
    """
    Generate an ASS (Advanced SubStation Alpha) script with dynamic active-word styling,
    modern rounded badges, spring-bounce effects, and 75% vertical positioning.
    """
    ass_primary = hex_to_ass_color(style.primary_color)
    ass_highlight = hex_to_ass_color(style.highlight_color)
    ass_outline = hex_to_ass_color(style.stroke_color)
    ass_shadow = hex_to_ass_color(style.shadow_color, 0.8)
    ass_box = hex_to_ass_color(style.box_color, style.box_opacity)

    # Scaling relative to 720p base
    scale = play_res_y / 720.0
    scaled_font_size = max(18, int(style.font_size * scale))
    scaled_radius = max(4, int(style.box_radius * scale))
    scaled_pad_x = max(10, int(style.box_padding_x * scale))
    scaled_pad_y = max(6, int(style.box_padding_y * scale))

    # Center placement: 75% distance from top (25% from bottom) by default
    cx = play_res_x / 2.0
    cy = play_res_y * (style.pos_y / 100.0)

    # Base ASS Style
    # Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour,
    # Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline,
    # Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
    bold_val = -1 if style.bold else 0
    italic_val = -1 if style.italic else 0

    styles = [
        f"Style: Default,{style.font_name},{scaled_font_size},{ass_primary},{ass_highlight},{ass_outline},{ass_shadow},"
        f"{bold_val},{italic_val},0,0,100,100,0,0,1,{style.stroke_width:.1f},{style.shadow_depth:.1f},5,20,20,0,1",
        f"Style: BoxBadge,{style.font_name},{scaled_font_size},{ass_box},{ass_box},&H00000000&,&H00000000&,"
        f"0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1",
    ]

    header = [
        "[Script Info]",
        "Title: Stickman Captions",
        "ScriptType: v4.00+",
        f"PlayResX: {play_res_x}",
        f"PlayResY: {play_res_y}",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, "
        "Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
    ] + styles + [
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]

    dialogue_lines: List[str] = []

    for chunk_idx, chunk in enumerate(chunks):
        words = chunk.words
        if not words:
            continue

        full_text = " ".join(
            (w.punctuated_word.upper() if style.all_caps else w.punctuated_word) for w in words
        )

        # Layer 0: Rounded Badge Background
        if style.has_box:
            tw, th = measure_text_dimensions(full_text, style.font_name, scaled_font_size)
            bw = min(float(play_res_x - 40), tw + scaled_pad_x * 2.0)
            bh = max(th + scaled_pad_y * 2.0, float(int(scaled_font_size * 1.4)))
            bx = cx - (bw / 2.0)
            by = cy - (bh / 2.0)
            r = min(float(scaled_radius), bw / 2.0, bh / 2.0)
            path = make_rounded_rect_path(bw, bh, r)

            chunk_start_str = format_ass_time(chunk.start)
            chunk_end_str = format_ass_time(chunk.end)
            dialogue_lines.append(
                f"Dialogue: 0,{chunk_start_str},{chunk_end_str},BoxBadge,,0,0,0,,{{\\an7\\pos({bx:.1f},{by:.1f})\\p1}}{path}{{\\p0}}"
            )

        # Layer 1: Text with active-word highlights and effects
        text_layer = 1 if style.has_box else 0
        pos_tag = f"{{\\an5\\pos({cx:.1f},{cy:.1f})}}"

        # Karaoke Wipe Effect
        if style.effect_type == "KARAOKE_WIPE":
            formatted_words = []
            for w in words:
                text = w.punctuated_word.upper() if style.all_caps else w.punctuated_word
                dur_cs = max(10, int((w.end - w.start) * 100))
                formatted_words.append(f"{{\\kf{dur_cs}}}{text}")
            
            line_text = pos_tag + " ".join(formatted_words)
            start_str = format_ass_time(chunk.start)
            end_str = format_ass_time(chunk.end)
            dialogue_lines.append(f"Dialogue: {text_layer},{start_str},{end_str},Default,,0,0,0,,{line_text}")

        # Active Word Highlight / Bounce / Pop Effect
        else:
            for idx, active_word in enumerate(words):
                seg_start = active_word.start
                if idx < len(words) - 1:
                    seg_end = words[idx + 1].start
                else:
                    seg_end = max(active_word.end, chunk.end)

                if seg_end <= seg_start:
                    seg_end = seg_start + 0.1

                formatted_words = []
                for w_idx, w in enumerate(words):
                    text = w.punctuated_word.upper() if style.all_caps else w.punctuated_word
                    if w_idx == idx:
                        # Spring-bounce / pop transform tag
                        if style.name == "colorsplosion":
                            anim = "{\\t(0,90,\\fscx118\\fscy118)\\t(90,180,\\fscx100\\fscy100)}"
                            palette = ["#FF007F", "#FFE600", "#00F0FF", "#39FF14", "#FF5E00", "#BF00FF"]
                            cur_highlight = hex_to_ass_color(palette[(chunk_idx * 3 + idx) % len(palette)])
                        elif style.effect_type in ("POP", "SPRING_BOUNCE"):
                            anim = "{\\t(0,100,\\fscx112\\fscy112)\\t(100,200,\\fscx100\\fscy100)}"
                            cur_highlight = ass_highlight
                        elif style.effect_type == "GLOW":
                            anim = "{\\blur4\\t(0,150,\\blur8)\\t(150,300,\\blur4)}"
                            cur_highlight = ass_highlight
                        else:
                            anim = ""
                            cur_highlight = ass_highlight
                        formatted_words.append(f"{anim}{{\\c{cur_highlight}}}{text}{{\\c{ass_primary}}}")
                    else:
                        formatted_words.append(text)

                line_text = pos_tag + " ".join(formatted_words)
                start_str = format_ass_time(seg_start)
                end_str = format_ass_time(seg_end)
                dialogue_lines.append(f"Dialogue: {text_layer},{start_str},{end_str},Default,,0,0,0,,{line_text}")

    return "\n".join(header + dialogue_lines) + "\n"


def burn_subtitles_and_mux_audio(
    video_path: str,
    audio_path: str,
    ass_path: str,
    output_path: str,
    threads: int = 2,
) -> str:
    """Burn ASS subtitles into the MP4 and mux narration audio using FFmpeg."""
    escaped_ass = escape_ffmpeg_ass_path(ass_path)
    vf_filter = f"ass='{escaped_ass}'"

    cmd = [
        "ffmpeg", "-y",
        "-threads", str(threads),
        "-i", video_path,
        "-i", audio_path,
        "-vf", vf_filter,
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "16",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        "-movflags", "+faststart",
        output_path
    ]

    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"FFmpeg caption burning failed: {res.stderr}")

    return output_path


def add_captions(
    video_path: str,
    audio_path: Optional[str] = None,
    script_text: Optional[str] = None,
    style_name: str = "hormozi-bold",
    pos_y: Optional[float] = None,
    output_path: Optional[str] = None,
) -> str:
    """
    High-level API: adds stylized subtitles and audio to a video.
    """
    if not os.path.isfile(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")

    # Inspect video resolution
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "csv=s=x:p=0",
        video_path
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    w, h = 1280, 720
    if res.returncode == 0 and "x" in res.stdout:
        parts = res.stdout.strip().split("x")
        try:
            w, h = int(parts[0]), int(parts[1])
        except Exception:
            pass

    # Extract audio if missing
    temp_audio = None
    if not audio_path or not os.path.isfile(audio_path):
        temp_audio = tempfile.mktemp(suffix=".mp3")
        subprocess.check_call(["ffmpeg", "-y", "-i", video_path, "-vn", "-ar", "16000", "-ac", "1", temp_audio],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        audio_path = temp_audio

    # Get word timestamps
    words = get_word_timings(audio_path, script_text=script_text)
    
    # Load style preset
    style = get_preset(style_name)
    if pos_y is not None:
        style.pos_y = float(pos_y)

    chunks = chunk_words(words, max_words_per_chunk=style.words_per_chunk)
    ass_content = build_ass_subtitles(chunks, style, play_res_x=w, play_res_y=h)

    ass_path = tempfile.mktemp(suffix=".ass")
    with open(ass_path, "w", encoding="utf-8") as f:
        f.write(ass_content)

    if not output_path:
        base, ext = os.path.splitext(video_path)
        output_path = f"{base}_captioned{ext}"

    try:
        burn_subtitles_and_mux_audio(video_path, audio_path, ass_path, output_path)
    finally:
        if os.path.isfile(ass_path):
            try:
                os.remove(ass_path)
            except Exception:
                pass
        if temp_audio and os.path.isfile(temp_audio):
            try:
                os.remove(temp_audio)
            except Exception:
                pass

    return output_path


def format_srt_time(seconds: float) -> str:
    """Format seconds into SRT timestamp HH:MM:SS,mmm."""
    seconds = max(0.0, float(seconds))
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int(round((seconds - int(seconds)) * 1000))
    if millis >= 1000:
        millis = 999
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def format_vtt_time(seconds: float) -> str:
    """Format seconds into WebVTT timestamp HH:MM:SS.mmm."""
    seconds = max(0.0, float(seconds))
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int(round((seconds - int(seconds)) * 1000))
    if millis >= 1000:
        millis = 999
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"


def export_srt(chunks: List[ChunkItem], output_path: str) -> str:
    """Export subtitle chunks to SubRip (.srt) sidecar file."""
    lines = []
    for idx, ch in enumerate(chunks, 1):
        s = format_srt_time(ch.start)
        e = format_srt_time(ch.end)
        lines.append(f"{idx}\n{s} --> {e}\n{ch.text}\n")
    content = "\n".join(lines)
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)
    return output_path


def export_vtt(chunks: List[ChunkItem], output_path: str) -> str:
    """Export subtitle chunks to WebVTT (.vtt) sidecar file."""
    lines = ["WEBVTT\n"]
    for idx, ch in enumerate(chunks, 1):
        s = format_vtt_time(ch.start)
        e = format_vtt_time(ch.end)
        lines.append(f"{idx}\n{s} --> {e}\n{ch.text}\n")
    content = "\n".join(lines)
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)
    return output_path
