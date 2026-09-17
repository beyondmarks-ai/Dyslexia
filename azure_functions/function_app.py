"""Secured HTTP gateway for question generation and Azure Speech."""

from __future__ import annotations

import base64
import json
import logging

import azure.functions as func

from services.question_service import generate_question_set
from services.speech_service import synthesize, transcribe


app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)


def _json_response(payload: dict, status_code: int = 200) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps(payload),
        status_code=status_code,
        mimetype="application/json",
    )


def _error_response(exc: Exception) -> func.HttpResponse:
    logging.exception("Dyslexia API request failed")
    if isinstance(exc, (ValueError, KeyError, TypeError)):
        return _json_response({"error": str(exc)}, 400)
    return _json_response({"error": "The Azure service request failed."}, 502)


@app.route(route="health", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def health(req: func.HttpRequest) -> func.HttpResponse:
    return _json_response({"status": "ok"})


@app.route(route="questions", methods=["POST"])
def questions(req: func.HttpRequest) -> func.HttpResponse:
    try:
        return _json_response(generate_question_set())
    except Exception as exc:
        return _error_response(exc)


@app.route(route="speech/transcribe", methods=["POST"])
def speech_transcribe(req: func.HttpRequest) -> func.HttpResponse:
    try:
        encoded = req.get_json()["audio_base64"]
        audio = base64.b64decode(encoded, validate=True)
        if len(audio) > 10 * 1024 * 1024:
            raise ValueError("Audio must be 10 MB or smaller.")
        return _json_response(transcribe(audio))
    except Exception as exc:
        return _error_response(exc)


@app.route(route="speech/synthesize", methods=["POST"])
def speech_synthesize(req: func.HttpRequest) -> func.HttpResponse:
    try:
        text = req.get_json()["text"]
        audio = synthesize(text)
        return _json_response({"audio_base64": base64.b64encode(audio).decode("ascii")})
    except Exception as exc:
        return _error_response(exc)
