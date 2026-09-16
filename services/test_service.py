"""Scoring helpers shared by the Streamlit workflow."""

from __future__ import annotations

import re
from typing import Iterable, Sequence


def normalize_text(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", value.lower()))


def score_answers(answers: Iterable[str], expected: Iterable[str]) -> dict[str, float | int]:
    pairs = list(zip(answers, expected))
    correct = sum(normalize_text(answer) == normalize_text(target) for answer, target in pairs)
    total = len(pairs)
    return {
        "total": total,
        "correct": correct,
        "incorrect": total - correct,
        "accuracy": correct / total if total else 0.0,
    }


def score_recalled_words(answer: str, expected: Sequence[str]) -> float:
    attempted = normalize_text(answer).split()
    matches = sum(a == b.lower() for a, b in zip(attempted, expected))
    return matches / len(expected) if expected else 0.0


def speed_score(elapsed_minutes: float, fastest: float = 3, slowest: float = 30) -> float:
    """Preserve the original app's clipped linear speed calculation."""
    return max(0.0, min(1.0, 1 - (elapsed_minutes - fastest) / (slowest - fastest)))
