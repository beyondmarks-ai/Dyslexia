"""Streamlit interface for the existing dyslexia screening research model."""

from __future__ import annotations

import json
import random
import time
import uuid
from pathlib import Path

import pandas as pd
import streamlit as st

from services.model_service import ModelServiceError, feature_importance, predict
from services.speech_service import is_configured, transcribe
from services.test_service import score_answers, score_recalled_words, speed_score

ROOT = Path(__file__).resolve().parent
AUDIO_DIR = ROOT / "Audios_memory"
STEPS = ["Vocabulary", "Memory", "Reading", "Optional speech", "Result"]
DISCLAIMER = (
    "This application is a research/educational screening tool and does not provide "
    "a medical diagnosis. A qualified professional should perform any formal assessment."
)
MEMORY_WORDS = [
    ["Apple", "Lettuce", "House", "River", "Dog", "Book", "Cooking"],
    ["Dog", "Cat", "Rabbit", "Horse", "Sheep", "Cow", "Goat"],
    ["Table", "Chair", "Sofa", "Bed", "Desk", "Lamp", "Shelf"],
    ["River", "Lake", "Ocean", "Pond", "Stream", "Beach", "Waterfall"],
    ["Red", "Blue", "Green", "Yellow", "Pink", "Black", "White"],
    ["Car", "Bus", "Train", "Plane", "Boat", "Bike", "Truck"],
    ["Rain", "Snow", "Sun", "Cloud", "Wind", "Storm", "Thunder"],
    ["Pen", "Pencil", "Eraser", "Paper", "Book", "Notebook", "Ruler"],
    ["Tree", "Flower", "Grass", "Leaf", "Seed", "Branch", "Bush"],
    ["Shirt", "Pants", "Socks", "Jacket", "Hat", "Gloves", "Scarf"],
]
READING_QUESTIONS = [
    {"prompt": "Maya packed a blue coat because the morning was cold. Why did Maya pack a coat?", "options": ["It was cold", "It was raining", "It was new"], "answer": "It was cold"},
    {"prompt": "Choose the word that completes the sentence: The bird built a ___ in the tree.", "options": ["nest", "net", "next"], "answer": "nest"},
    {"prompt": "Which word rhymes with light?", "options": ["night", "late", "lot"], "answer": "night"},
    {"prompt": "Which sentence has the same meaning as 'The small dog ran quickly'?", "options": ["The little dog ran fast", "The large dog walked", "The dog slept"], "answer": "The little dog ran fast"},
]
PHONEMES = [
    ("Bat and Pat", "Bat_Pat.mp3", "Different"),
    ("Ship and Sheep", "Ship_Sheep.mp3", "Different"),
    ("Cat and Cat", "Cat_Cat.mp3", "Same"),
    ("Light and Right", "Light_Right.mp3", "Different"),
    ("Thin and Tin", "Thin_Tin.mp3", "Different"),
]
SURVEY_QUESTIONS = [
    "I find it difficult to read words or letters in the correct order.",
    "I have trouble spelling common words correctly.",
    "I mix up similar-looking letters such as b and d.",
    "I find it hard to concentrate when reading or writing.",
    "I have difficulty remembering sequences such as phone numbers.",
]

st.set_page_config(page_title="Dyslexia Screening Research Application", page_icon="DS", layout="wide")
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Atkinson+Hyperlegible:wght@400;700&family=Crimson+Pro:wght@600;700&display=swap');
    :root { --ink:#1e1b4b; --muted:#475569; --primary:#4f46e5; --surface:#fff; --border:#c7d2fe; }
    html, body, [class*="css"] { font-family:'Atkinson Hyperlegible',Arial,sans-serif; color:var(--ink); }
    .stApp { background:linear-gradient(145deg,#f8fafc 0%,#eef2ff 100%); }
    .block-container { max-width:1060px; padding-top:2rem; padding-bottom:4rem; }
    h1,h2,h3 { font-family:'Crimson Pro',Georgia,serif; color:var(--ink); letter-spacing:-.01em; }
    .hero { background:#fff; border:1px solid var(--border); border-radius:24px; padding:clamp(24px,5vw,56px); box-shadow:0 14px 34px rgba(79,70,229,.09); }
    .eyebrow { color:#4338ca; font-weight:700; text-transform:uppercase; letter-spacing:.08em; font-size:.82rem; }
    .lead { color:var(--muted); font-size:1.16rem; line-height:1.65; max-width:720px; }
    .notice { background:#fff7ed; border-left:5px solid #ea580c; border-radius:12px; padding:16px 18px; color:#431407; margin:18px 0; }
    .stepbar { display:flex; gap:8px; margin:8px 0 28px; flex-wrap:wrap; }
    .step { padding:9px 13px; border-radius:999px; border:1px solid var(--border); background:#fff; color:#475569; font-weight:700; }
    .step.active { background:#4f46e5; color:#fff; border-color:#4f46e5; }
    .step.done { background:#e0e7ff; color:#312e81; }
    .result-card { background:#fff; border:1px solid var(--border); border-radius:18px; padding:22px; min-height:126px; box-shadow:0 8px 22px rgba(30,27,75,.06); }
    .result-label { color:#475569; font-size:.9rem; }
    .result-value { color:#1e1b4b; font-size:1.8rem; font-weight:700; margin-top:5px; }
    div.stButton > button, div.stFormSubmitButton > button { min-height:48px; border-radius:12px; font-weight:700; transition:box-shadow .18s ease,background .18s ease; }
    div.stButton > button:focus-visible, div.stFormSubmitButton > button:focus-visible { outline:3px solid #f97316; outline-offset:2px; }
    [data-testid="stForm"] { background:#fff; border:1px solid var(--border); border-radius:18px; padding:20px; }
    [data-testid="stForm"] label,
    [data-testid="stForm"] [data-testid="stWidgetLabel"] p,
    [data-testid="stForm"] [data-testid="stMarkdownContainer"] p,
    [data-testid="stForm"] [role="radiogroup"] p { color:#1e1b4b !important; }
    [data-testid="stForm"] input { color:#1e1b4b !important; background:#fff; }
    [data-testid="stForm"] * { color:#000 !important; }
    div.stFormSubmitButton > button, div.stFormSubmitButton > button * { color:#fff !important; }
    @media (prefers-reduced-motion:reduce) { * { transition:none !important; scroll-behavior:auto !important; } }
    @media (max-width:600px) { .block-container{padding:1rem 1rem 3rem}.hero{padding:24px}.step{font-size:.82rem;padding:7px 9px} }
    </style>
    """,
    unsafe_allow_html=True,
)


def initialize() -> None:
    for key, value in {"page": "home", "session_id": str(uuid.uuid4()), "memory_stage": "memorize"}.items():
        st.session_state.setdefault(key, value)


def navigate(page: str) -> None:
    st.session_state.page = page
    if page == "vocabulary" and "start_time" not in st.session_state:
        st.session_state.start_time = time.time()
        st.session_state.vocab_started = time.time()
    if page == "reading":
        st.session_state.setdefault("reading_started", time.time())


def restart() -> None:
    st.session_state.clear()
    initialize()


def progress(active: str) -> None:
    current = STEPS.index(active)
    items = "".join(
        f'<span class="step {"active" if i == current else "done" if i < current else ""}">{i + 1}. {name}</span>'
        for i, name in enumerate(STEPS)
    )
    st.markdown(f'<div class="stepbar" aria-label="Screening progress">{items}</div>', unsafe_allow_html=True)


def metric_card(label: str, value: str) -> None:
    st.markdown(f'<div class="result-card"><div class="result-label">{label}</div><div class="result-value">{value}</div></div>', unsafe_allow_html=True)


def render_home() -> None:
    st.markdown(
        """
        <div class="hero"><div class="eyebrow">Research application</div>
        <h1>Dyslexia screening, presented with care.</h1>
        <p class="lead">A short, guided activity covering vocabulary, memory, reading, listening and self-reported experiences. It uses the project's existing trained model and keeps additional reading and speech observations separate.</p></div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(f'<div class="notice"><strong>Important:</strong> {DISCLAIMER}</div>', unsafe_allow_html=True)
    left, middle, right = st.columns(3)
    left.metric("Estimated time", "10–15 min")
    middle.metric("Core sections", "3")
    right.metric("Speech", "Optional")
    st.button("Start screening", type="primary", use_container_width=True, on_click=navigate, args=("instructions",))


def render_instructions() -> None:
    st.title("Before you begin")
    st.write("Choose a quiet place, use headphones for listening items, and answer without outside help. You can stop at any time.")
    st.info("No name, email address or other direct identifier is requested. Your session has a random identifier and is not stored by this application.")
    st.markdown(f'<div class="notice"><strong>Consent and scope:</strong> {DISCLAIMER}</div>', unsafe_allow_html=True)
    acknowledged = st.checkbox("I understand that this is not a medical diagnosis.")
    st.button("Begin vocabulary", type="primary", disabled=not acknowledged, on_click=navigate, args=("vocabulary",))


def render_vocabulary() -> None:
    progress("Vocabulary")
    st.title("Vocabulary")
    st.write("Choose the word that best completes each sentence.")
    if "vocab_questions" not in st.session_state:
        questions = json.loads((ROOT / "questions_vocab.json").read_text(encoding="utf-8"))["questions"]
        st.session_state.vocab_questions = random.sample(questions, min(10, len(questions)))
    with st.form("vocabulary_form"):
        answers = [st.radio(q["question"], q["options"], index=None, key=f"vocab_{i}") or "" for i, q in enumerate(st.session_state.vocab_questions)]
        submitted = st.form_submit_button("Continue to memory", type="primary")
    if submitted:
        if any(not answer for answer in answers):
            st.error("Please answer every vocabulary question before continuing.")
            return
        metrics = score_answers(answers, [q["correct_answer"] for q in st.session_state.vocab_questions])
        metrics["response_seconds"] = round(time.time() - st.session_state.vocab_started, 1)
        st.session_state.vocabulary = metrics
        st.session_state.Language_vocab = metrics["accuracy"]
        st.session_state.memory_sequences = ["".join(map(str, random.sample(range(10), 6))) for _ in range(3)]
        st.session_state.memory_audio_ids = random.sample(range(10), 3)
        navigate("memory")
        st.rerun()


def render_memory() -> None:
    progress("Memory")
    st.title("Memory")
    if st.session_state.memory_stage == "memorize":
        st.write("Study each six-digit sequence. When ready, continue; the sequences will be hidden.")
        for index, sequence in enumerate(st.session_state.memory_sequences, 1):
            st.code(f"Sequence {index}: {' '.join(sequence)}", language=None)
        if st.button("I have memorized the sequences", type="primary"):
            st.session_state.memory_stage = "recall"
            st.session_state.memory_started = time.time()
            st.rerun()
        return
    st.write("Enter the digit sequences, then listen once to each word list and recall the words in order.")
    with st.form("memory_form"):
        sequence_answers = [st.text_input(f"Sequence {i + 1}", max_chars=12) for i in range(3)]
        audio_answers = []
        for i, audio_id in enumerate(st.session_state.memory_audio_ids):
            st.audio(str(AUDIO_DIR / f"audio_{audio_id + 1}.wav"), format="audio/wav")
            audio_answers.append(st.text_input(f"Words recalled from audio {i + 1}"))
        submitted = st.form_submit_button("Continue to reading", type="primary")
    if submitted:
        if any(not value.strip() for value in sequence_answers + audio_answers):
            st.error("Please attempt every memory item before continuing.")
            return
        sequence_metrics = score_answers(sequence_answers, st.session_state.memory_sequences)
        expected_lists = [MEMORY_WORDS[i] for i in st.session_state.memory_audio_ids]
        recall_scores = [score_recalled_words(answer, expected) for answer, expected in zip(audio_answers, expected_lists)]
        recall_exact = sum(score == 1 for score in recall_scores)
        score = (sequence_metrics["accuracy"] + sum(recall_scores) / len(recall_scores)) / 2
        st.session_state.memory = {"total": 6, "correct": sequence_metrics["correct"] + recall_exact, "incorrect": 6 - sequence_metrics["correct"] - recall_exact, "accuracy": score, "recall_score": sum(recall_scores) / len(recall_scores), "response_seconds": round(time.time() - st.session_state.memory_started, 1)}
        st.session_state.Memory = score
        navigate("reading")
        st.rerun()


def render_reading() -> None:
    progress("Reading")
    st.title("Reading and language")
    st.write("The reading score is supplementary. The visual, listening and questionnaire scores retain the existing model's six-feature input contract.")
    with st.form("reading_form"):
        st.subheader("Reading comprehension")
        reading_answers = [st.radio(q["prompt"], q["options"], index=None, key=f"reading_{i}") or "" for i, q in enumerate(READING_QUESTIONS)]
        st.subheader("Visual discrimination")
        count_d = st.number_input("How many letter d characters are in: b p q d b d p q b d p q?", 0, 12, value=None)
        visual_set = st.multiselect("Select each different letter shown in: b p q d d p", ["b", "p", "q", "d"])
        odd_one = st.radio("Choose the odd one out", ["○ ○ ○", "○ ○ ■", "○ ○ ○ ○"], index=None)
        st.subheader("Listening discrimination")
        phoneme_answers = []
        for i, (label, filename, _) in enumerate(PHONEMES):
            st.audio(str(AUDIO_DIR / filename), format="audio/mp3")
            phoneme_answers.append(st.radio(label, ["Same", "Different"], index=None, key=f"phoneme_{i}") or "")
        st.audio(str(AUDIO_DIR / "Bake.mp3"), format="audio/mp3")
        rhyme_answers = st.multiselect("Which words rhyme with Bake?", ["Take", "Back", "Lake", "Bike"])
        stress_answer = st.radio("Which syllable is stressed in Photography?", ["First", "Second", "Third", "Fourth"], index=None)
        st.audio(str(AUDIO_DIR / "The_quick_brown.mp3"), format="audio/mp3")
        sentence_answer = st.text_input("Write the sentence you heard")
        st.subheader("Reading experiences")
        survey_options = ["No", "Not often", "Sometimes", "Often", "Yes"]
        survey_answers = [st.radio(question, survey_options, index=None, key=f"survey_{i}") for i, question in enumerate(SURVEY_QUESTIONS)]
        submitted = st.form_submit_button("Continue to optional speech", type="primary")
    if submitted:
        required = reading_answers + phoneme_answers + [odd_one, stress_answer, sentence_answer] + survey_answers
        if count_d is None or any(not answer for answer in required):
            st.error("Please attempt every item before continuing. The speech section remains optional.")
            return
        reading = score_answers(reading_answers, [q["answer"] for q in READING_QUESTIONS])
        reading["response_seconds"] = round(time.time() - st.session_state.reading_started, 1)
        visual = (int(count_d == 3) + int(set(visual_set) == {"b", "p", "q", "d"}) + int(odd_one == "○ ○ ■")) / 3
        phoneme = sum(answer == expected for answer, (_, _, expected) in zip(phoneme_answers, PHONEMES)) * 0.1
        rhyme = len(set(rhyme_answers) & {"Take", "Lake"}) / 2 * 0.1
        stress = 0.1 if stress_answer == "Second" else 0
        sentence = 0.3 if score_answers([sentence_answer], ["The quick brown fox jumps over the lazy dog"])["correct"] else 0
        audio = phoneme + rhyme + stress + sentence
        survey_points = {"No": 0, "Not often": 1, "Sometimes": 2, "Often": 3, "Yes": 4}
        survey = sum(survey_points[answer] for answer in survey_answers) / 20
        st.session_state.reading = reading
        st.session_state.Visual_discrimination = visual
        st.session_state.Audio_Discrimination = audio
        st.session_state.Survey_Score = survey
        navigate("speech")
        st.rerun()


def finish_screening() -> None:
    elapsed = (time.time() - st.session_state.start_time) / 60
    features = {"Language_vocab": st.session_state.Language_vocab, "Memory": st.session_state.Memory, "Speed": speed_score(elapsed), "Visual_discrimination": st.session_state.Visual_discrimination, "Audio_Discrimination": st.session_state.Audio_Discrimination, "Survey_Score": st.session_state.Survey_Score}
    st.session_state.elapsed_minutes = elapsed
    st.session_state.prediction = predict(features)
    navigate("result")


def render_speech() -> None:
    progress("Optional speech")
    st.title("Optional read aloud")
    st.write("Read this sentence aloud: “The bright bird rested beside the quiet river.” Speech metrics are supplementary and are never sent to the prediction model.")
    st.caption("If enabled, your recording is sent to the configured Azure Speech resource for transcription and is not retained by this app.")
    if is_configured():
        recording = st.audio_input("Record your reading")
        if st.button("Analyze recording", disabled=recording is None):
            try:
                st.session_state.speech = transcribe(recording.getvalue())
                st.success("Speech transcription completed.")
            except (RuntimeError, ValueError) as exc:
                st.warning(str(exc))
    else:
        st.info("Azure Speech is not configured. You can continue without recording; the model result is unaffected.")
    if "speech" in st.session_state:
        st.write(f"Transcription: {st.session_state.speech['transcription']}")
    label = "Continue to result" if "speech" in st.session_state else "Skip speech and view result"
    if st.button(label, type="primary"):
        try:
            finish_screening()
            st.rerun()
        except (ValueError, ModelServiceError) as exc:
            st.error(str(exc))


def render_results() -> None:
    progress("Result")
    result = st.session_state.get("prediction")
    if not result:
        navigate("home")
        st.rerun()
    st.markdown('<div class="eyebrow">Screening result</div>', unsafe_allow_html=True)
    st.title(f"{result['indication']} screening indication")
    st.write("This category is the output of the existing trained model. It is not a diagnosis or a measure of ability.")
    cols = st.columns(4)
    with cols[0]: metric_card("Model result", result["indication"])
    with cols[1]: metric_card("Model confidence", f"{result['confidence']:.0%}" if result["confidence"] is not None else "Unavailable")
    with cols[2]: metric_card("Vocabulary", f"{st.session_state.vocabulary['accuracy']:.0%}")
    with cols[3]: metric_card("Memory", f"{st.session_state.memory['accuracy']:.0%}")
    detail_cols = st.columns(3)
    detail_cols[0].metric("Memory recall", f"{st.session_state.memory['recall_score']:.0%}")
    detail_cols[1].metric("Reading", f"{st.session_state.reading['accuracy']:.0%}")
    detail_cols[2].metric("Session time", f"{st.session_state.elapsed_minutes:.1f} min")
    st.subheader("Screening summary")
    summary = pd.DataFrame([
        ["Vocabulary", st.session_state.vocabulary["total"], st.session_state.vocabulary["correct"], st.session_state.vocabulary["incorrect"], st.session_state.vocabulary["accuracy"], st.session_state.vocabulary["response_seconds"]],
        ["Memory", st.session_state.memory["total"], st.session_state.memory["correct"], st.session_state.memory["incorrect"], st.session_state.memory["accuracy"], st.session_state.memory["response_seconds"]],
        ["Reading (supplementary)", st.session_state.reading["total"], st.session_state.reading["correct"], st.session_state.reading["incorrect"], st.session_state.reading["accuracy"], st.session_state.reading["response_seconds"]],
    ], columns=["Section", "Questions", "Correct", "Incorrect", "Accuracy", "Response time (s)"])
    st.dataframe(summary, hide_index=True, use_container_width=True, column_config={"Accuracy": st.column_config.ProgressColumn(format="percent", min_value=0, max_value=1)})
    st.caption(f"Total session time: {st.session_state.elapsed_minutes:.1f} minutes. Reading response time: {st.session_state.reading['response_seconds']:.0f} seconds.")
    st.subheader("Model inputs")
    model_frame = pd.DataFrame({"Feature": result["features"].keys(), "Score": result["features"].values()})
    st.bar_chart(model_frame, x="Feature", y="Score", horizontal=True, height=320)
    st.caption("Only these six original, ordered features were scaled and sent to model.pkl. Reading and speech metrics are supplementary.")
    with st.expander("What these scores mean"):
        st.write("Accuracy is the share of correct responses. Memory recall includes partial credit for words recalled in the original order. The speed score uses the original app's 3-to-30-minute scale. Survey answers describe reported experiences; they are not clinical findings.")
    importance = feature_importance()
    if importance:
        st.subheader("How the fitted model weighs features")
        importance_frame = pd.DataFrame({"Feature": importance.keys(), "Global importance": importance.values()})
        st.bar_chart(importance_frame, x="Feature", y="Global importance", horizontal=True, height=320)
        st.caption("Global Random Forest impurity importance across the fitted model—not a causal explanation and not an individual clinical finding.")
    if result["probabilities"]:
        with st.expander("Model class probabilities"):
            st.dataframe(pd.DataFrame([result["probabilities"]]), hide_index=True, use_container_width=True)
    if "speech" in st.session_state:
        with st.expander("Optional speech metrics"):
            st.json(st.session_state.speech)
    st.markdown(f'<div class="notice"><strong>Important:</strong> {DISCLAIMER}</div>', unsafe_allow_html=True)
    st.button("Start a new screening", on_click=restart)


initialize()
page = st.session_state.page
if page == "home": render_home()
elif page == "instructions": render_instructions()
elif page == "vocabulary": render_vocabulary()
elif page == "memory": render_memory()
elif page == "reading": render_reading()
elif page == "speech": render_speech()
else: render_results()
