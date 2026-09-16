"""Optional Azure Speech transcription using managed identity/Azure CLI credentials."""

from __future__ import annotations

import os
import tempfile
import wave
from pathlib import Path


def is_configured() -> bool:
    return bool(
        os.getenv("AZURE_SPEECH_ENDPOINT")
        and os.getenv("AZURE_SPEECH_RESOURCE_ID")
    )


def transcribe(audio: bytes) -> dict:
    if not audio:
        raise ValueError("Record audio before requesting transcription.")
    if not is_configured():
        raise RuntimeError("Azure Speech is not configured; the screening can continue without it.")

    try:
        import azure.cognitiveservices.speech as speechsdk
        from azure.identity import DefaultAzureCredential
    except ImportError as exc:
        raise RuntimeError("Install requirements-azure.txt to enable optional speech.") from exc

    endpoint = os.environ["AZURE_SPEECH_ENDPOINT"]
    resource_id = os.environ["AZURE_SPEECH_RESOURCE_ID"]
    token = DefaultAzureCredential().get_token(
        "https://cognitiveservices.azure.com/.default"
    ).token
    config = speechsdk.SpeechConfig(endpoint=endpoint)
    config.authorization_token = f"aad#{resource_id}#{token}"
    config.speech_recognition_language = os.getenv("AZURE_SPEECH_LANGUAGE", "en-US")

    suffix = ".wav"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as handle:
        handle.write(audio)
        path = Path(handle.name)
    try:
        audio_config = speechsdk.audio.AudioConfig(filename=str(path))
        result = speechsdk.SpeechRecognizer(config, audio_config).recognize_once_async().get()
        if result.reason != speechsdk.ResultReason.RecognizedSpeech:
            detail = getattr(result, "error_details", None) or str(result.reason)
            raise RuntimeError(f"Azure Speech did not recognize the recording: {detail}")
        duration = _wav_duration(path)
        words = result.text.split()
        return {
            "transcription": result.text,
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
