# Dyslexia Screening

A guided Streamlit research application for dyslexia screening exercises. It combines vocabulary, memory, reading, listening and self-reported activities with the repository's existing trained model.

> **Important:** This is an educational/research screening tool, not a medical device or diagnosis. Consult a qualified professional for formal assessment.

## Quick start

Requirements: Python 3.11 and Git. The pinned dependencies match the saved scikit-learn artifacts.

```powershell
git clone https://github.com/beyondmarks-ai/Dyslexia.git
cd Dyslexia
py -3.11 -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

Open <http://localhost:8501>.

If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope Process Bypass` once in that terminal, or use the virtual environment directly:

```powershell
.\\.venv\\Scripts\\python.exe -m pip install -r requirements.txt
.\\.venv\\Scripts\\streamlit.exe run app.py
```

## What the app does

1. Explains the scope and obtains acknowledgement.
2. Runs vocabulary and memory exercises.
3. Runs reading, visual discrimination, listening and questionnaire activities.
4. Optionally sends an explicitly recorded reading to Azure Speech for transcription.
5. Produces a screening indication and score summary.

The model receives exactly these six values, in this order:

`Language_vocab`, `Memory`, `Speed`, `Visual_discrimination`, `Audio_Discrimination`, `Survey_Score`

Reading and speech measurements are supplementary. They are not additional model features.

## Run checks

```powershell
python -m unittest discover -s tests -v
```

The tests cover artifact loading, input validation, scoring, the complete Streamlit flow and the form contrast regression.

## Optional Azure Speech

Install the optional dependencies and configure Azure Speech before starting the app:

```powershell
pip install -r requirements-azure.txt
$env:AZURE_SPEECH_ENDPOINT = "https://<resource>.cognitiveservices.azure.com/"
$env:AZURE_SPEECH_RESOURCE_ID = "/subscriptions/<id>/resourceGroups/<group>/providers/Microsoft.CognitiveServices/accounts/<resource>"
$env:AZURE_SPEECH_LANGUAGE = "en-US"
az login
streamlit run app.py
```

The app uses `DefaultAzureCredential`, so Azure CLI authentication works locally and managed identity can be used in Azure Container Apps. If Speech is not configured or fails, the core screening still works.

| Variable | Required | Description |
|---|---|---|
| `AZURE_SPEECH_ENDPOINT` | Speech only | Azure Speech endpoint |
| `AZURE_SPEECH_RESOURCE_ID` | Speech only | Azure resource ID used for Entra authentication |
| `AZURE_SPEECH_LANGUAGE` | No | Recognition locale; defaults to `en-US` |

## Run with Docker

```powershell
docker build -t dyslexia-screening .
docker run --rm -p 8501:8501 dyslexia-screening
```

Open <http://localhost:8501> after the container starts.

## Deploy to Azure Container Apps

Prerequisites: Azure CLI, an active subscription, Docker/Container Apps build support, and `az login`.

```powershell
az login
az account show
.\\scripts\\deploy_azure.ps1 `
  -ResourceGroup <resource-group> `
  -AppName dyslexia-screening `
  -Location centralindia `
  -Environment <container-apps-environment>
```

The script deploys from the repository, exposes port 8501 over HTTPS, and configures 0.5 CPU, 1 GiB memory, zero minimum replicas and one maximum replica. It does not train the model, provision a GPU or delete resources.

See [docs/AZURE.md](docs/AZURE.md) for identity configuration, environment variables and operational notes.

## Repository layout

| Path | Purpose |
|---|---|
| `app.py` | Streamlit application and screening workflow |
| `services/model_service.py` | Artifact loading, validation, scaling and inference |
| `services/test_service.py` | Deterministic score calculations |
| `services/speech_service.py` | Optional Azure Speech integration |
| `model.pkl`, `scaler.pkl` | Existing inference artifacts |
| `Audios_memory/` | Audio exercises |
| `questions_vocab.json` | Vocabulary question bank |
| `tests/` | Standard-library and Streamlit tests |
| `docs/` | Architecture, model and Azure notes |
| `Dockerfile` | Container runtime definition |

## Model and limitations

The saved artifacts are used as-is; this repository does not retrain them during startup. An artifact-consistent evaluation measured 92.75% accuracy on the original 400-row held-out partition. That is dataset performance, not clinical accuracy, and the data has not been established here as clinically validated or population-representative.

The application keeps screening data in the active Streamlit session and does not configure application storage. Optional speech audio is sent to Azure Speech only when the user records audio and Azure is configured. It is not used for model inference.

For technical details, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and [docs/CURRENT_MODEL.md](docs/CURRENT_MODEL.md).

## Troubleshooting

- **Port 8501 is busy:** run `streamlit run app.py --server.port 8502`.
- **Model loading fails:** use Python 3.11 and install the pinned `requirements.txt`.
- **Speech is unavailable:** verify all Speech variables and `az login`; the optional section can be skipped.
- **Docker cannot build:** confirm Docker is running and run the build command from the repository root.
