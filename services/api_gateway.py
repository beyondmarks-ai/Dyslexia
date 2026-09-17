"""HTTP client for the secured Dyslexia Azure Function gateway."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path

import tomllib


SECRETS_PATH = Path(__file__).resolve().parents[1] / ".streamlit" / "secrets.toml"


def _settings() -> tuple[str | None, str | None]:
    url = os.getenv("DYSLEXIA_API_URL")
    key = os.getenv("DYSLEXIA_API_KEY")
    if (not url or not key) and SECRETS_PATH.exists():
        try:
            values = tomllib.loads(SECRETS_PATH.read_text(encoding="utf-8")).get("api", {})
            url = url or values.get("url")
            key = key or values.get("key")
        except (OSError, tomllib.TOMLDecodeError):
            pass
    return url, key


def is_configured() -> bool:
    return all(_settings())


def post_json(route: str, payload: dict, timeout: int = 60) -> dict:
    if not is_configured():
        raise RuntimeError("The Dyslexia API gateway is not configured.")
    base_url, key = _settings()
    url = f"{base_url.rstrip('/')}/api/{route.lstrip('/')}"
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-functions-key": key,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Dyslexia API request failed ({exc.code}): {detail}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError(f"Dyslexia API request failed: {exc}") from exc
