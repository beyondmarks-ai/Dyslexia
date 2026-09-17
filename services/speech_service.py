"""Optional Azure Speech transcription using managed identity/Azure CLI credentials."""

from __future__ import annotations

import os
import json
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import wave
import base64
from functools import lru_cache
from pathlib import Path
from xml.sax.saxutils import escape

from services.api_gateway import is_configured as gateway_is_configured, post_json


def is_configured() -> bool:
    return gateway_is_configured() or bool(
        os.getenv("AZURE_SPEECH_ENDPOINT")
        and os.getenv("AZURE_SPEECH_RESOURCE_ID")
        and os.getenv("AZURE_SPEECH_REGION")
    )


def transcribe(audio: bytes) -> dict:
    if not audio:
        raise ValueError("Record audio before requesting transcription.")
    if gateway_is_configured():
        return post_json(
            "speech/transcribe",
            {"audio_base64": base64.b64encode(audio).decode("ascii")},
            timeout=60,
        )
    if not is_configured():
        raise RuntimeError("Azure Speech is not configured; the screening can continue without it.")

    try:
        from azure.identity import DefaultAzureCredential
    except ImportError as exc:
        raise RuntimeError("Install requirements-azure.txt to enable optional speech.") from exc

    endpoint = os.environ["AZURE_SPEECH_ENDPOINT"]
    region = os.environ["AZURE_SPEECH_REGION"]
    language = os.getenv("AZURE_SPEECH_LANGUAGE", "en-US")
    token = DefaultAzureCredential().get_token(
        "https://cognitiveservices.azure.com/.default"
    ).token

    suffix = ".wav"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as handle:
        handle.write(audio)
        path = Path(handle.name)
    try:
        query = urllib.parse.urlencode({"language": language, "format": "detailed"})
        url = (
            f"{endpoint.rstrip('/')}"
            "/stt/speech/recognition/conversation/cognitiveservices/v1"
            f"?{query}"
        )
        request = urllib.request.Request(
            url,
            data=audio,
            headers={
                "Authorization": f"Bearer {token}",
                "Ocp-Apim-Subscription-Region": region,
                "Content-Type": "audio/wav; codecs=audio/pcm; samplerate=16000",
                "Accept": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                result = json.load(response)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Azure Speech request failed ({exc.code}): {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Azure Speech request failed: {exc.reason}") from exc

        if result.get("RecognitionStatus") != "Success":
            detail = result.get("RecognitionStatus", "unknown response")
            raise RuntimeError(f"Azure Speech did not recognize the recording: {detail}")
        transcription = result.get("DisplayText", "")
        duration = _wav_duration(path)
        words = transcription.split()
        return {
            "transcription": transcription,
            "duration_seconds": duration,
            "words_attempted": len(words),
            "recognized_words": len(words),
        }
    finally:
        path.unlink(missing_ok=True)


def _wav_duration(path: Path) -> float | None:
    try:
        with wave.open(str(path), "rb") as recording:
            return recording.getnframes() / recording.getframerate()
    except (wave.Error, OSError, ZeroDivisionError):
        return None


@lru_cache(maxsize=64)
def synthesize(text: str) -> bytes:
    """Create a short WAV prompt using Azure Speech and keyless authentication."""
    text = text.strip()
    if not text or len(text) > 300:
        raise ValueError("Speech prompt must contain between 1 and 300 characters.")
    if gateway_is_configured():
        result = post_json("speech/synthesize", {"text": text}, timeout=60)
        try:
            return base64.b64decode(result["audio_base64"], validate=True)
        except (KeyError, TypeError, ValueError) as exc:
            raise RuntimeError("Dyslexia API returned invalid synthesized audio.") from exc
    if not is_configured() or not os.getenv("AZURE_SPEECH_REGION"):
        raise RuntimeError("Azure Speech synthesis is not configured.")
    try:
        from azure.identity import DefaultAzureCredential
    except ImportError as exc:
        raise RuntimeError("Install requirements-azure.txt to enable speech synthesis.") from exc

    endpoint = os.environ["AZURE_SPEECH_ENDPOINT"].rstrip("/")
    region = os.environ["AZURE_SPEECH_REGION"]
    voice = os.getenv("AZURE_SPEECH_VOICE", "en-US-AvaMultilingualNeural")
    token = DefaultAzureCredential().get_token(
        "https://cognitiveservices.azure.com/.default"
    ).token
    ssml = (
        '<speak version="1.0" xml:lang="en-US">'
        f'<voice name="{escape(voice)}">{escape(text)}</voice></speak>'
    ).encode("utf-8")
    request = urllib.request.Request(
        f"{endpoint}/tts/cognitiveservices/v1",
        data=ssml,
        headers={
            "Authorization": f"Bearer {token}",
            "Ocp-Apim-Subscription-Region": region,
            "X-Microsoft-OutputFormat": "riff-16khz-16bit-mono-pcm",
            "Content-Type": "application/ssml+xml",
            "User-Agent": "dyslexia-screening",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Azure speech synthesis failed ({exc.code}): {detail}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError(f"Azure speech synthesis failed: {exc}") from exc
