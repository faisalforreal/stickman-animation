"""Flexible Text-to-Speech (TTS) engine for stickman_anim.

Supports:
1. Google Gemini Speech API (default model: gemini-3.8-flash-tts, default voice: Charon).
2. OpenAI-compatible /v1/audio/speech endpoints.
3. ElevenLabs /v1/text-to-speech endpoints.
4. Custom REST endpoints configurable via .env.
5. Offline / mock audio generation for testing without API keys.
"""

import os
import re
import json
import base64
import wave
import math
import struct
import subprocess
from typing import Optional, Dict, Any, Tuple


def load_env(env_path: Optional[str] = None) -> Dict[str, str]:
    """
    Lightweight .env loader that searches current working directory,
    git/project roots, or home directory without external dependencies.
    """
    candidates = []
    if env_path and os.path.isfile(env_path):
        candidates.append(env_path)

    cwd = os.getcwd()
    candidates.extend([
        os.path.join(cwd, ".env"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".env"),
        os.path.join(os.path.expanduser("~"), ".gemini", ".env"),
        os.path.join(os.path.expanduser("~"), ".env"),
    ])

    loaded = {}
    for p in candidates:
        if os.path.isfile(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        if "=" in line:
                            key, val = line.split("=", 1)
                            key = key.strip()
                            val = val.strip().strip('"').strip("'")
                            if key not in os.environ:
                                os.environ[key] = val
                            loaded[key] = val
                break
            except Exception:
                continue
    return loaded


# Automatically load environment variables on import
load_env()


def get_audio_duration(audio_path: str) -> float:
    """Inspect audio file duration in seconds using ffprobe or wave header fallback."""
    if not os.path.isfile(audio_path):
        return 0.0

    # 1. Try ffprobe
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            audio_path
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode == 0 and res.stdout.strip():
            return max(0.1, float(res.stdout.strip()))
    except Exception:
        pass

    # 2. Try native wave module if it's a WAV file
    try:
        with wave.open(audio_path, "rb") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            if rate > 0:
                return max(0.1, float(frames) / float(rate))
    except Exception:
        pass

    # Fallback estimate based on file size if MP3 (~16KB per sec at 128kbps)
    try:
        size = os.path.getsize(audio_path)
        return max(1.0, float(size) / 16000.0)
    except Exception:
        return 3.0


def create_mock_tone_wav(text: str, output_path: str, duration_sec: Optional[float] = None) -> str:
    """Generate a clean synthetic speech-length WAV file for offline testing."""
    if duration_sec is None:
        words = text.split()
        duration_sec = max(1.5, len(words) * 0.35 + 0.5)

    sample_rate = 24000
    total_samples = int(sample_rate * duration_sec)
    freq = 220.0  # gentle low tone

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with wave.open(output_path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        
        raw_data = bytearray()
        for i in range(total_samples):
            # Smoothly modulated amplitude
            t = float(i) / sample_rate
            env = 0.5 * (1.0 - math.cos(2 * math.pi * t / duration_sec)) if t < 0.1 or t > (duration_sec - 0.1) else 1.0
            val = int(env * 6000 * math.sin(2 * math.pi * freq * t))
            raw_data.extend(struct.pack("<h", max(-32767, min(32767, val))))
        wf.writeframes(raw_data)

    return output_path


def _generate_gemini_tts(
    text: str,
    output_path: str,
    api_key: str,
    model: str = "gemini-3.8-flash-tts",
    voice: str = "Charon",
    endpoint: Optional[str] = None,
) -> str:
    """Call Google Gemini REST API to generate speech audio."""
    import requests

    if not endpoint:
        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    else:
        endpoint = endpoint.replace("{model}", model)

    # Support either query parameter or x-goog-api-key header
    url = endpoint
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key,
    }
    if "key=" not in url:
        url = f"{url}?key={api_key}"

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": text}
                ]
            }
        ],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {
                    "prebuiltVoiceConfig": {
                        "voiceName": voice
                    }
                }
            }
        }
    }

    import time
    for attempt in range(4):
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        if resp.status_code == 429 and attempt < 3:
            wait_sec = 25
            try:
                err_data = resp.json()
                for d in err_data.get("error", {}).get("details", []):
                    if d.get("@type", "").endswith("RetryInfo"):
                        rd = d.get("retryDelay", "25s")
                        wait_sec = max(5, int(float(rd.rstrip("s")) + 1))
            except Exception:
                pass
            print(f"[Gemini TTS] Rate limit hit. Waiting {wait_sec}s before retry ({attempt + 1}/3)...")
            time.sleep(wait_sec)
            continue
        elif resp.status_code != 200:
            raise RuntimeError(f"Gemini TTS error ({resp.status_code}): {resp.text}")
        break

    data = resp.json()
    candidates = data.get("candidates", [])
    if not candidates:
        raise RuntimeError(f"Gemini TTS returned no candidates: {data}")

    parts = candidates[0].get("content", {}).get("parts", [])
    audio_bytes = None
    mime_type = "audio/wav"

    for part in parts:
        inline_data = part.get("inlineData") or part.get("inline_data")
        if inline_data and inline_data.get("data"):
            audio_bytes = base64.b64decode(inline_data["data"])
            mime_type = inline_data.get("mimeType") or inline_data.get("mime_type") or mime_type
            break

    if not audio_bytes:
        raise RuntimeError(f"No inline audio data found in Gemini response: {data}")

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(audio_bytes)

    return output_path


def _generate_openai_tts(
    text: str,
    output_path: str,
    api_key: str,
    model: str = "tts-1",
    voice: str = "alloy",
    endpoint: Optional[str] = None,
) -> str:
    """Call OpenAI-compatible audio speech endpoint."""
    import requests

    url = endpoint or "https://api.openai.com/v1/audio/speech"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "input": text,
        "voice": voice,
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    if resp.status_code != 200:
        raise RuntimeError(f"OpenAI TTS error ({resp.status_code}): {resp.text}")

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(resp.content)

    return output_path


def _generate_elevenlabs_tts(
    text: str,
    output_path: str,
    api_key: str,
    model: str = "eleven_monolingual_v1",
    voice: str = "21m00Tcm4TlvDq8ikWAM",  # Voice ID
    endpoint: Optional[str] = None,
) -> str:
    """Call ElevenLabs text-to-speech API."""
    import requests

    url = endpoint or f"https://api.elevenlabs.io/v1/text-to-speech/{voice}"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    payload = {
        "text": text,
        "model_id": model,
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    if resp.status_code != 200:
        raise RuntimeError(f"ElevenLabs TTS error ({resp.status_code}): {resp.text}")

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(resp.content)

    return output_path


def _generate_custom_tts(
    text: str,
    output_path: str,
    endpoint: str,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    voice: Optional[str] = None,
    headers: Optional[Dict[str, str]] = None,
    payload_template: Optional[Any] = None,
) -> str:
    """Call an arbitrary custom REST TTS endpoint with flexible templating."""
    import requests

    url = endpoint.replace("{model}", model or "").replace("{voice}", voice or "").replace("{key}", api_key or "")
    
    req_headers = {"Content-Type": "application/json"}
    if headers:
        for k, v in headers.items():
            req_headers[k] = v.replace("{key}", api_key or "").replace("{model}", model or "")
    elif api_key:
        req_headers["Authorization"] = f"Bearer {api_key}"

    if payload_template:
        if isinstance(payload_template, str):
            payload_str = payload_template.replace("{text}", text).replace("{voice}", voice or "").replace("{model}", model or "")
            try:
                payload = json.loads(payload_str)
            except Exception:
                payload = payload_str
        else:
            payload = payload_template
    else:
        payload = {"text": text, "voice": voice or "default", "model": model or "default"}

    resp = requests.post(url, headers=req_headers, json=payload if isinstance(payload, dict) else None, data=payload if isinstance(payload, str) else None, timeout=60)
    if resp.status_code != 200:
        raise RuntimeError(f"Custom TTS error ({resp.status_code}): {resp.text}")

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    content_type = resp.headers.get("Content-Type", "")
    if "json" in content_type:
        data = resp.json()
        audio_b64 = data.get("audio") or data.get("data")
        if audio_b64:
            with open(output_path, "wb") as f:
                f.write(base64.b64decode(audio_b64))
            return output_path

    with open(output_path, "wb") as f:
        f.write(resp.content)

    return output_path


def generate_speech(
    text: str,
    output_path: Optional[str] = None,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    voice: Optional[str] = None,
    api_key: Optional[str] = None,
    endpoint: Optional[str] = None,
    headers: Optional[Dict[str, str]] = None,
    payload_template: Optional[Any] = None,
) -> str:
    """
    Main entry point for speech generation.
    Pulls defaults from .env, with priority given to function arguments.
    Default voice is 'Charon'. Default model is 'gemini-3.8-flash-tts'.
    """
    load_env()

    prov = (provider or os.getenv("TTS_PROVIDER") or "gemini").lower()
    mod = model or os.getenv("TTS_MODEL") or ("gemini-3.8-flash-tts" if prov == "gemini" else "tts-1")
    voi = voice or os.getenv("TTS_VOICE") or ("Charon" if prov == "gemini" else "alloy")
    key = api_key or os.getenv("TTS_API_KEY") or os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")
    ep = endpoint or os.getenv("TTS_ENDPOINT")

    if not output_path:
        ext = ".wav" if prov == "gemini" else ".mp3"
        output_path = os.path.join(os.getcwd(), f"speech_{voi.lower()}{ext}")

    if not key and prov != "custom":
        print(f"[stickman_anim.tts] No API key found for provider '{prov}'. Generating synthetic tone preview.")
        return create_mock_tone_wav(text, output_path)

    if prov == "gemini":
        return _generate_gemini_tts(text, output_path, key, mod, voi, ep)
    elif prov == "openai":
        return _generate_openai_tts(text, output_path, key, mod, voi, ep)
    elif prov == "elevenlabs":
        return _generate_elevenlabs_tts(text, output_path, key, mod, voi, ep)
    elif prov == "custom":
        if not ep:
            raise ValueError("TTS_ENDPOINT must be set when using provider 'custom'")
        return _generate_custom_tts(text, output_path, ep, key, mod, voi, headers, payload_template)
    else:
        raise ValueError(f"Unsupported TTS provider: '{prov}'. Choose 'gemini', 'openai', 'elevenlabs', or 'custom'.")
