# Architecture

```text
Streamlit UI (app.py)
  ├─ vocabulary, memory, reading/listening/questionnaire workflow
  ├─ services/test_service.py → deterministic scoring
  ├─ services/model_service.py → validate → scaler.pkl → model.pkl
  └─ services/speech_service.py → optional Azure Speech transcription
```

The application uses a pseudonymous in-memory session ID. It asks for no direct identifiers and persists no screening data. Blob Storage was intentionally not added because the current workflow does not require storage.

The main sequence is Home → Instructions → Vocabulary → Memory → Reading → Optional Speech → Result. Reading and speech observations are shown separately. Only the six documented model features enter inference.

The result displays the predicted screening indication, class probability when supported, section metrics, the exact model inputs and global Random Forest feature importance. Importance is descriptive of the fitted model, not causal or clinical evidence.
