"""Safe inference wrapper for the repository's existing trained artifacts."""

from __future__ import annotations

import math
import pickle
from functools import lru_cache
from pathlib import Path
from typing import Mapping

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
FEATURES = (
    "Language_vocab",
    "Memory",
    "Speed",
    "Visual_discrimination",
    "Audio_Discrimination",
    "Survey_Score",
)
LABELS = {0: "High", 1: "Moderate", 2: "Low"}
LIKELIHOOD_WEIGHTS = {"High": 1.0, "Moderate": 0.5, "Low": 0.0}


class ModelServiceError(RuntimeError):
    """Raised when model artifacts or prediction inputs are invalid."""


@lru_cache(maxsize=1)
def load_artifacts():
    """Load the existing model and scaler once per process."""
    try:
        with (ROOT / "model.pkl").open("rb") as handle:
            model = pickle.load(handle)
        with (ROOT / "scaler.pkl").open("rb") as handle:
            scaler = pickle.load(handle)
    except (OSError, EOFError, pickle.UnpicklingError, AttributeError, ImportError) as exc:
        raise ModelServiceError(f"Could not load the existing model artifacts: {exc}") from exc

    expected = list(FEATURES)
    artifact_features = list(getattr(scaler, "feature_names_in_", expected))
    if artifact_features != expected:
        raise ModelServiceError(
            f"Scaler feature order is {artifact_features}; expected {expected}."
        )
    if getattr(model, "n_features_in_", len(expected)) != len(expected):
        raise ModelServiceError("Model does not accept the documented six features.")
    return model, scaler


def validate_features(values: Mapping[str, float]) -> dict[str, float]:
    missing = [name for name in FEATURES if name not in values]
    extra = [name for name in values if name not in FEATURES]
    if missing or extra:
        raise ValueError(f"Expected exactly {list(FEATURES)}; missing={missing}, extra={extra}.")

    validated: dict[str, float] = {}
    for name in FEATURES:
        try:
            value = float(values[name])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{name} must be numeric.") from exc
        if not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError(f"{name} must be between 0 and 1.")
        validated[name] = value
    return validated


def predict(values: Mapping[str, float]) -> dict:
    """Scale validated features in their original order and run model.pkl."""
    model, scaler = load_artifacts()
    validated = validate_features(values)
    frame = pd.DataFrame([[validated[name] for name in FEATURES]], columns=FEATURES)

    try:
        scaled = scaler.transform(frame)
        label = int(model.predict(scaled)[0])
        probabilities = None
        confidence = None
        if hasattr(model, "predict_proba"):
            row = model.predict_proba(scaled)[0]
            probabilities = {
                LABELS.get(int(class_id), str(class_id)): float(probability)
                for class_id, probability in zip(model.classes_, row)
            }
            confidence = probabilities.get(LABELS.get(label, str(label)))
    except Exception as exc:
        raise ModelServiceError(f"The existing model could not make a prediction: {exc}") from exc

    if label not in LABELS:
        raise ModelServiceError(f"The model returned unsupported label {label!r}.")
    return {
        "label": label,
        "indication": LABELS[label],
        "confidence": confidence,
        "probabilities": probabilities,
        "features": validated,
        "likelihood": screening_likelihood(probabilities),
    }


def screening_likelihood(probabilities: Mapping[str, float] | None) -> float | None:
    """Return a 0-1 model-derived screening score, not a clinical probability."""
    if not probabilities:
        return None
    return sum(
        float(probabilities.get(label, 0.0)) * weight
        for label, weight in LIKELIHOOD_WEIGHTS.items()
    )


def feature_importance() -> dict[str, float] | None:
    """Return fitted global impurity importance when the estimator exposes it."""
    model, _ = load_artifacts()
    estimator = getattr(model, "best_estimator_", model)
    values = getattr(estimator, "feature_importances_", None)
    if values is None or len(values) != len(FEATURES):
        return None
    return dict(sorted(zip(FEATURES, map(float, values)), key=lambda item: item[1], reverse=True))
