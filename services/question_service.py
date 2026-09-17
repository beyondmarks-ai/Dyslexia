"""Generate bounded screening questions with Azure OpenAI and Entra ID."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
import uuid

from services.api_gateway import is_configured as gateway_is_configured, post_json


VOCABULARY_COUNT = 10
READING_COUNT = 4


def is_configured() -> bool:
    return gateway_is_configured() or bool(
        os.getenv("AZURE_OPENAI_ENDPOINT")
        and os.getenv("AZURE_OPENAI_DEPLOYMENT")
    )


def generate_question_set() -> dict:
    """Return validated vocabulary and reading questions for one session."""
    if gateway_is_configured():
        return validate_question_set(post_json("questions", {}, timeout=90))
    if not is_configured():
        raise RuntimeError("Azure question generation is not configured.")

    try:
        from azure.identity import DefaultAzureCredential
    except ImportError as exc:
        raise RuntimeError("Install requirements-azure.txt to enable AI questions.") from exc

    endpoint = os.environ["AZURE_OPENAI_ENDPOINT"].rstrip("/")
    deployment = urllib.parse.quote(os.environ["AZURE_OPENAI_DEPLOYMENT"], safe="")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")
    token = DefaultAzureCredential().get_token(
        "https://cognitiveservices.azure.com/.default"
    ).token
    schema = _question_schema()
    payload = {
        "messages": [
            {
                "role": "system",
                "content": (
                    "You create neutral English-language screening exercises, not medical advice. "
                    "Use plain, unambiguous language. Every item must have exactly three unique "
                    "options and exactly one clearly correct answer. correct_answer must exactly "
                    "match one option. Every vocabulary question must be a sentence with the "
                    "literal blank ___. Every reading prompt must contain a self-contained one- "
                    "or two-sentence passage followed by an explicit question; never refer to a "
                    "passage or story that is not included. Avoid health, diagnosis, distress, "
                    "politics, violence, personal data, trick questions, and culture-specific knowledge."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Variation seed: {uuid.uuid4()}. Generate {VOCABULARY_COUNT} varied sentence "
                    f"completion vocabulary items and {READING_COUNT} short reading comprehension "
                    "items, plus two different neutral 7-14 word sentences: one for audio dictation "
                    "and one for reading aloud. Return only the sentence content, never an instruction "
                    "such as 'read this sentence'. Avoid stock phrases such as 'the quick brown fox'. "
                    "Keep each option under 12 words."
                ),
            },
        ],
        "temperature": 0.9,
        "max_tokens": 2400,
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": "screening_questions", "strict": True, "schema": schema},
        },
    }
    url = (
        f"{endpoint}/openai/deployments/{deployment}/chat/completions"
        f"?{urllib.parse.urlencode({'api-version': api_version})}"
    )
    last_validation_error = None
    for attempt in range(3):
        payload["messages"][1]["content"] += f" Attempt nonce: {uuid.uuid4()}."
        if attempt:
            payload["messages"][1]["content"] += (
                " The previous set failed validation. Check blanks, passages, unique options, "
                "and exact answer-option matches carefully."
            )
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                result = json.load(response)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Azure question generation failed ({exc.code}): {detail}") from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            raise RuntimeError(f"Azure question generation failed: {exc}") from exc

        try:
            content = result["choices"][0]["message"]["content"]
            generated = json.loads(content)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise RuntimeError("Azure returned an invalid question response.") from exc
        try:
            return validate_question_set(generated)
        except ValueError as exc:
            last_validation_error = exc
    raise RuntimeError(f"Azure returned invalid questions after three attempts: {last_validation_error}")


def validate_question_set(value: dict) -> dict:
    if not isinstance(value, dict):
        raise ValueError("Question set must be an object.")
    vocabulary = _validate_items(value.get("vocabulary"), VOCABULARY_COUNT, "question")
    reading = _validate_reading_items(value.get("reading"))
    dictation = _validate_sentence(value.get("dictation_sentence"), "dictation")
    read_aloud = _validate_sentence(value.get("read_aloud_sentence"), "read-aloud")
    if dictation.casefold() == read_aloud.casefold():
        raise ValueError("Dictation and read-aloud sentences must differ.")
    return {
        "vocabulary": vocabulary,
        "reading": reading,
        "dictation_sentence": dictation,
        "read_aloud_sentence": read_aloud,
    }


def _validate_sentence(value, label: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"The {label} prompt must be text.")
    sentence = value.strip()
    word_count = len(sentence.rstrip(".!?").split())
    if not 7 <= word_count <= 14 or sentence[-1:] not in ".!?":
        raise ValueError(f"The {label} prompt must be one complete 7-14 word sentence.")
    lowered = sentence.casefold()
    if any(phrase in lowered for phrase in ("read this sentence", "repeat this sentence", "say this sentence", "quick brown fox")):
        raise ValueError(f"The {label} prompt must contain fresh sentence content only.")
    return sentence


def _validate_items(items, expected_count: int, prompt_key: str) -> list[dict]:
    if not isinstance(items, list) or len(items) != expected_count:
        raise ValueError(f"Expected exactly {expected_count} {prompt_key} items.")
    validated = []
    prompts = set()
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("Each question must be an object.")
        prompt = item.get(prompt_key)
        options = item.get("options")
        answer = item.get("correct_answer")
        if not isinstance(prompt, str) or not prompt.strip() or prompt in prompts:
            raise ValueError("Question prompts must be non-empty and unique.")
        if prompt_key == "question" and "___" not in prompt:
            raise ValueError("Every vocabulary question must include an explicit blank.")
        if (
            not isinstance(options, list)
            or len(options) != 3
            or any(not isinstance(option, str) or not option.strip() for option in options)
            or len(set(options)) != 3
        ):
            raise ValueError("Every question must contain three unique options.")
        if answer not in options:
            raise ValueError("Every correct answer must exactly match an option.")
        prompts.add(prompt)
        validated.append({prompt_key: prompt, "options": options, "correct_answer": answer})
    return validated


def _validate_reading_items(items) -> list[dict]:
    if not isinstance(items, list) or len(items) != READING_COUNT:
        raise ValueError(f"Expected exactly {READING_COUNT} reading items.")
    normalized = []
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("Each reading item must be an object.")
        passage = item.get("passage")
        question = item.get("question")
        # Question sets returned by this module are already normalized to a
        # single ``prompt`` field for the Streamlit UI.  Accept that trusted,
        # normalized representation too, so a Function gateway response can
        # be validated again by a client without changing its shape.
        existing_prompt = item.get("prompt")
        if existing_prompt is not None:
            if not isinstance(existing_prompt, str) or len(existing_prompt.strip()) < 30:
                raise ValueError("Every reading item must include a self-contained passage.")
            if "?" not in existing_prompt:
                raise ValueError("Every reading item must include an explicit question.")
            normalized.extend(
                _validate_items(
                    [
                        {
                            "prompt": existing_prompt.strip(),
                            "options": item.get("options"),
                            "correct_answer": item.get("correct_answer"),
                        }
                    ],
                    1,
                    "prompt",
                )
            )
            continue
        if not isinstance(passage, str) or len(passage.strip()) < 30:
            raise ValueError("Every reading item must include a self-contained passage.")
        if not isinstance(question, str) or not question.strip() or "?" not in question:
            raise ValueError("Every reading item must include an explicit question.")
        candidate = {
            "prompt": f"{passage.strip()}\n\n{question.strip()}",
            "options": item.get("options"),
            "correct_answer": item.get("correct_answer"),
        }
        normalized.extend(_validate_items([candidate], 1, "prompt"))
    if len({item["prompt"] for item in normalized}) != READING_COUNT:
        raise ValueError("Reading prompts must be unique.")
    return normalized


def _question_schema() -> dict:
    def items(prompt_key: str, count: int) -> dict:
        return {
            "type": "array",
            "minItems": count,
            "maxItems": count,
            "items": {
                "type": "object",
                "properties": {
                    prompt_key: {"type": "string"},
                    "options": {
                        "type": "array",
                        "minItems": 3,
                        "maxItems": 3,
                        "items": {"type": "string"},
                    },
                    "correct_answer": {"type": "string"},
                },
                "required": [prompt_key, "options", "correct_answer"],
                "additionalProperties": False,
            },
        }

    return {
        "type": "object",
        "properties": {
            "vocabulary": items("question", VOCABULARY_COUNT),
            "reading": {
                "type": "array",
                "minItems": READING_COUNT,
                "maxItems": READING_COUNT,
                "items": {
                    "type": "object",
                    "properties": {
                        "passage": {"type": "string"},
                        "question": {"type": "string"},
                        "options": {
                            "type": "array",
                            "minItems": 3,
                            "maxItems": 3,
                            "items": {"type": "string"},
                        },
                        "correct_answer": {"type": "string"},
                    },
                    "required": ["passage", "question", "options", "correct_answer"],
                    "additionalProperties": False,
                },
            },
            "dictation_sentence": {"type": "string"},
            "read_aloud_sentence": {"type": "string"},
        },
        "required": ["vocabulary", "reading", "dictation_sentence", "read_aloud_sentence"],
        "additionalProperties": False,
    }
