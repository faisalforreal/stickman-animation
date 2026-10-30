"""Audio Cues, Multi-Speaker Dialogue, Lip-Sync Amplitude, and Procedural SFX.

Provides:
- Script cue parser `@cue(name)` with exact frame and audio timestamp calculation.
- Multi-speaker dialogue parser and sequential audio assembly.
- Per-frame audio amplitude envelope extraction for driving character mouth lip-sync.
- Pure-Python procedural sound effects synthesizer (pop, click, whoosh, ding, pen_scratch).
- Audio track mixing with background music (BGM) ducking and loudness normalization.
"""

import math
import os
import random
import re
import struct
import subprocess
import wave
from typing import List, Tuple, Dict, Any, Optional
from .tts import generate_speech, get_audio_duration


# ------------------------------------------------------------------ 1. Script Cue Parser
CUE_PATTERN = re.compile(r"@cue\s*\(\s*([a-zA-Z0-9_\-]+)\s*\)")


def parse_cued_script(script_text: str) -> Tuple[str, List[Tuple[str, float]]]:
    """
    Parses `@cue(name)` markers from narration text.
    Returns:
    - clean_text: Text with cue markers removed (safe for TTS speech generation).
    - cue_fractions: List of (cue_name, progress_fraction [0.0..1.0]) indicating
      where in the script's speech flow each cue occurs based on word position.
    """
    words = script_text.split()
    clean_words = []
    cues_found = []

    for w in words:
        m = CUE_PATTERN.search(w)
        if m:
            cue_name = m.group(1)
            # Cue fires at current clean word position
            cues_found.append((cue_name, len(clean_words)))
            # If word had attached text e.g. "Ready!@cue(go)", keep non-cue part
            remaining = CUE_PATTERN.sub("", w).strip()
            if remaining:
                clean_words.append(remaining)
        else:
            clean_words.append(w)

    clean_text = " ".join(clean_words)
    total_words = max(1, len(clean_words))

    cue_fractions = [
        (name, min(1.0, max(0.0, word_idx / float(total_words))))
        for name, word_idx in cues_found
    ]
    return clean_text, cue_fractions


class CueTimeline:
    """Calculates cue trigger points across animation frames."""
    def __init__(self, cue_fractions: List[Tuple[str, float]], total_frames: int):
        self.total_frames = max(1, total_frames)
        self.cues: Dict[str, int] = {}
        for name, frac in cue_fractions:
            frame_idx = int(frac * (self.total_frames - 1))
            self.cues[name] = frame_idx

    def frame_at(self, cue_name: str) -> Optional[int]:
        return self.cues.get(cue_name)

    def has_fired(self, cue_name: str, current_frame: int) -> bool:
        """True if the cue has triggered on or before current_frame."""
        if cue_name not in self.cues:
            return False
        return current_frame >= self.cues[cue_name]

    def is_active(self, cue_name: str, current_frame: int, window: int = 6) -> bool:
        """True if the cue fired within the last `window` frames."""
        if cue_name not in self.cues:
            return False
        trigger = self.cues[cue_name]
        return trigger <= current_frame < (trigger + window)


# ------------------------------------------------------------------ 2. Multi-Speaker Dialogue
SPEAKER_PATTERN = re.compile(r"(?:\[Speaker:\s*([a-zA-Z0-9_\-]+)\]|^([a-zA-Z0-9_\-]+):)\s*(.+)$")


def parse_dialogue_script(script_text: str, default_speaker: str = "Host") -> List[Tuple[str, str]]:
    """
    Parses multi-speaker dialogue text lines formatted as:
    [Speaker: Charon] Hello everyone!
    or
    Host: Welcome back.
    """
    lines = [line.strip() for line in script_text.strip().splitlines() if line.strip()]
    dialogue: List[Tuple[str, str]] = []
    current_speaker = default_speaker

    for line in lines:
        m = SPEAKER_PATTERN.match(line)
        if m:
            speaker = (m.group(1) or m.group(2)).strip()
            content = m.group(3).strip()
            dialogue.append((speaker, content))
            current_speaker = speaker
        else:
            dialogue.append((current_speaker, line))

    return dialogue


def generate_dialogue_audio(
    dialogue: List[Tuple[str, str]],
    voice_map: Optional[Dict[str, str]] = None,
    output_path: str = "dialogue_master.wav",
    pause_seconds: float = 0.25,
) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Generates and joins speech for each dialogue line with individual speaker voices.
    Returns:
    - Master audio file path.
    - List of timeline speaker intervals: [{"speaker": name, "start": s, "end": e}, ...].
    """
    import tempfile
    voice_map = voice_map or {"Host": "Charon", "Charon": "Charon", "Puck": "Puck", "Fenrir": "Fenrir"}
    segment_files = []
    intervals = []
    current_time = 0.0

    temp_dir = tempfile.mkdtemp()
    for idx, (speaker, line) in enumerate(dialogue):
        voice = voice_map.get(speaker, "Charon")
        seg_path = os.path.join(temp_dir, f"seg_{idx:03d}_{speaker}.wav")
        # Generate speech segment
        actual_path = generate_speech(line, output_path=seg_path, voice=voice)
        dur = get_audio_duration(actual_path)

        start_t = current_time
        end_t = start_t + dur
        intervals.append({
            "speaker": speaker,
            "text": line,
            "start": round(start_t, 3),
            "end": round(end_t, 3)
        })
        segment_files.append(actual_path)
        current_time = end_t + pause_seconds

    # Stitch WAV files with pause silence
    rate = 24000
    all_frames = bytearray()
    silence_frames = int(rate * pause_seconds)
    silence_bytes = b"\x00\x00" * silence_frames

    for seg in segment_files:
        try:
            with wave.open(seg, "rb") as wf:
                rate = wf.getframerate()
                all_frames.extend(wf.readframes(wf.getnframes()))
                all_frames.extend(silence_bytes)
        except Exception:
            pass

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with wave.open(output_path, "wb") as out_wf:
        out_wf.setnchannels(1)
        out_wf.setsampwidth(2)
        out_wf.setframerate(rate)
        out_wf.writeframes(all_frames)

    return output_path, intervals


def get_active_speaker_at(intervals: List[Dict[str, Any]], current_time: float) -> Optional[str]:
    """Finds which speaker is currently talking at timestamp current_time."""
    for item in intervals:
        if item["start"] <= current_time <= item["end"]:
            return item["speaker"]
    return None


# ------------------------------------------------------------------ 3. Audio RMS Lip-Sync Amplitude
def calculate_rms_envelope(audio_path: str, fps: float, n_frames: int) -> List[float]:
    """
    Computes normalized RMS audio amplitude for every frame [0.0..1.0].
    Powers character mouth opening for speech lip-sync.
    """
    if not os.path.isfile(audio_path):
        return [0.0] * n_frames

    # Convert to mono 16-bit WAV if not already
    wav_path = audio_path
    if not audio_path.lower().endswith(".wav"):
        tmp_wav = audio_path + ".tmp.wav"
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", audio_path, "-ac", "1", "-ar", "24000", "-c:a", "pcm_s16le", tmp_wav]
        try:
            subprocess.run(cmd, check=True)
            wav_path = tmp_wav
        except Exception:
            return [0.0] * n_frames

    envelope = []
    try:
        with wave.open(wav_path, "rb") as wf:
            framerate = wf.getframerate()
            sampwidth = wf.getsampwidth()
            n_samples = wf.getnframes()
            raw_bytes = wf.readframes(n_samples)

        samples_per_video_frame = max(1, int(framerate / fps))
        # Unpack 16-bit PCM samples
        fmt = f"<{n_samples}h" if sampwidth == 2 else f"<{n_samples}b"
        samples = struct.unpack_from(fmt, raw_bytes)

        max_rms = 1e-4
        raw_rms = []
        for f in range(n_frames):
            idx0 = f * samples_per_video_frame
            idx1 = min(len(samples), idx0 + samples_per_video_frame)
            if idx0 >= len(samples):
                raw_rms.append(0.0)
                continue
            chunk = samples[idx0:idx1]
            if not chunk:
                raw_rms.append(0.0)
                continue
            sum_sq = sum(s * s for s in chunk)
            rms = math.sqrt(sum_sq / len(chunk))
            raw_rms.append(rms)
            if rms > max_rms:
                max_rms = rms

        envelope = [min(1.0, r / max_rms) for r in raw_rms]
    except Exception:
        envelope = [0.0] * n_frames

    if wav_path != audio_path and os.path.isfile(wav_path):
        try:
            os.remove(wav_path)
        except Exception:
            pass

    return envelope


# ------------------------------------------------------------------ 4. Pure-Python CC0 Procedural SFX
def synthesize_sfx(kind: str, output_path: str, sample_rate: int = 44100) -> str:
    """
    Pure-Python procedural sound effects synthesizer. Zero external audio files or dependencies.
    Produces 16-bit mono PCM WAV for cartoon stop-motion animations.
    """
    kind = kind.lower().strip()
    samples: List[float] = []

    if kind == "pop":
        # Bubble pop: rapid pitch drop from 600Hz to 120Hz over 0.08s
        dur = 0.08
        n_pts = int(sample_rate * dur)
        for i in range(n_pts):
            t = i / float(sample_rate)
            freq = 600.0 - 480.0 * (t / dur)
            phase = 2.0 * math.pi * freq * t
            decay = math.exp(-35.0 * t)
            samples.append(math.sin(phase) * decay)

    elif kind == "click":
        # Sharp mechanic switch click (2.5kHz damp pulse, 0.03s)
        dur = 0.03
        n_pts = int(sample_rate * dur)
        for i in range(n_pts):
            t = i / float(sample_rate)
            decay = math.exp(-120.0 * t)
            samples.append(math.sin(2.0 * math.pi * 2500.0 * t) * decay)

    elif kind == "whoosh":
        # Fast swoosh sweep from 250Hz up to 900Hz and down (0.22s)
        dur = 0.22
        n_pts = int(sample_rate * dur)
        for i in range(n_pts):
            t = i / float(sample_rate)
            prog = t / dur
            freq = 250.0 + 750.0 * math.sin(prog * math.pi)
            env = math.sin(prog * math.pi)
            # Add subtle pseudo-noise
            noise = (math.sin(i * 1.7) * 0.3)
            samples.append((math.sin(2.0 * math.pi * freq * t) + noise) * env)

    elif kind == "ding":
        # Bell / sparkle chime: 1200Hz + 2400Hz harmonics with long decay (0.5s)
        dur = 0.5
        n_pts = int(sample_rate * dur)
        for i in range(n_pts):
            t = i / float(sample_rate)
            decay1 = math.exp(-8.0 * t)
            decay2 = math.exp(-14.0 * t)
            h1 = math.sin(2.0 * math.pi * 1200.0 * t) * decay1 * 0.7
            h2 = math.sin(2.0 * math.pi * 2400.0 * t) * decay2 * 0.3
            samples.append(h1 + h2)

    elif kind == "pen_scratch":
        # Whiteboard marker / pencil scratch friction sound (0.15s)
        dur = 0.15
        n_pts = int(sample_rate * dur)
        for i in range(n_pts):
            t = i / float(sample_rate)
            # Modulated friction noise
            noise = math.sin(i * 3.1415 + math.sin(i * 0.1) * 5.0)
            env = math.sin((t / dur) * math.pi)
            samples.append(noise * env * 0.6)

    else:
        # Default neutral blip
        dur = 0.05
        n_pts = int(sample_rate * dur)
        for i in range(n_pts):
            t = i / float(sample_rate)
            samples.append(math.sin(2.0 * math.pi * 440.0 * t) * math.exp(-40.0 * t))

    # Convert float samples (-1.0 to 1.0) into 16-bit PCM bytes
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    raw_bytes = bytearray()
    for s in samples:
        clamped = max(-1.0, min(1.0, s))
        val = int(clamped * 32767.0)
        raw_bytes.extend(struct.pack("<h", val))

    with wave.open(output_path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(raw_bytes)

    return output_path


def mix_audio_tracks(
    voice_path: str,
    bgm_path: Optional[str] = None,
    output_path: str = "master_audio.wav",
    bgm_volume: float = 0.12,
    normalize: bool = True
) -> str:
    """
    Mixes voiceover narration with optional background music (ducked) and normalizes loudness.
    Uses FFmpeg if available, or returns voice_path as clean master.
    """
    import shutil
    if not shutil.which("ffmpeg") or not os.path.isfile(voice_path):
        return voice_path

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    if bgm_path and os.path.isfile(bgm_path):
        # Auto-duck BGM behind voice track and mix
        filter_str = (
            f"[1:a]volume={bgm_volume}[bgm]; "
            f"[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=2[mixed]"
        )
        if normalize:
            filter_str += "; [mixed]loudnorm[out]"
            out_map = "[out]"
        else:
            out_map = "[mixed]"

        cmd = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", voice_path,
            "-stream_loop", "-1", "-i", bgm_path,
            "-filter_complex", filter_str,
            "-map", out_map,
            "-c:a", "pcm_s16le", output_path
        ]
    else:
        # Loudness normalization on voice alone
        if normalize:
            cmd = [
                "ffmpeg", "-y", "-loglevel", "error",
                "-i", voice_path,
                "-af", "loudnorm",
                "-c:a", "pcm_s16le", output_path
            ]
        else:
            return voice_path

    try:
        subprocess.run(cmd, check=True)
        return output_path
    except Exception:
        return voice_path
