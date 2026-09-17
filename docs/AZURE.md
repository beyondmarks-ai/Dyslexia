# Azure deployment

## Current deployment

- URL: `https://dyslexia-screening.ashyforest-be110feb.centralindia.azurecontainerapps.io`
- Container App: `dyslexia-screening`
- Resource group: `lyriclatch-rg`
- Environment: `lyriclatch-env`
- Resources: 0.5 CPU, 1 GiB memory, 0–1 replicas

## Cost-conscious services

The default deployment needs only Azure Container Apps and its supporting registry/environment. The script sets 0.5 CPU, 1 GiB memory, zero minimum replicas and one maximum replica. Scale-to-zero reduces idle compute cost, though registry, logs and build storage may still incur small charges. Consult the current Azure pricing pages for the selected region; this repository does not hard-code estimates that may become stale.

Azure Speech is optional. No Speech or Storage resource is required for the core application. Blob Storage was not added because results are intentionally not persisted.

Azure OpenAI question generation is optional. The current deployment uses the
`question-generator` deployment on `dyslexia-ai-617db5` with the low-cost
`gpt-4.1-nano` model. It generates questions and session-specific dictation/read-aloud
prompts only; the repository's existing model
continues to calculate the screening result.

## Client gateway

`dyslexia-api-617db5` is a Python 3.11 Azure Function App in the same resource
group. It exposes a health endpoint plus Function-key-protected question and
Speech endpoints. Its managed identity has Cognitive Services OpenAI User on
`dyslexia-ai-617db5` and Cognitive Services User on `dyslexia-speech-617db5`.

This means a submitted/local copy of the Streamlit project can call Azure-backed
features using only `DYSLEXIA_API_URL` and `DYSLEXIA_API_KEY`; it does not require
Azure CLI login, an Azure subscription, or any Azure resource key. Store the
Function key in `.streamlit/secrets.toml` (from the tracked example) or an
environment variable, never in Git. The Function key authorizes use of the shared
gateway, so rotate it if it is exposed.

Deploy gateway source after changes:

```powershell
.\scripts\deploy_function.ps1 -FunctionApp dyslexia-api-617db5
```

## Authenticate and deploy

```powershell
az login
az account show
.\scripts\deploy_azure.ps1 -ResourceGroup lyriclatch-rg -AppName dyslexia-screening -Location centralindia -Environment lyriclatch-env
```

The deployed application reuses `lyriclatch-env` and its registry to avoid creating duplicate supporting resources. Omit `-Environment` only when the subscription can create a new Container Apps environment. The script never deletes resources and stops immediately if any Azure command fails.

## Optional Azure Speech

Install `requirements-azure.txt` in the image and configure:

| Variable | Purpose |
|---|---|
| `AZURE_SPEECH_ENDPOINT` | Custom subdomain endpoint for the Speech resource |
| `AZURE_SPEECH_RESOURCE_ID` | Full Azure resource ID used for Entra authentication |
| `AZURE_SPEECH_REGION` | Azure region containing the Speech resource |
| `AZURE_SPEECH_LANGUAGE` | Recognition locale; defaults to `en-US` |

Assign the Container App managed identity the Cognitive Services User role on the Speech resource. Locally, `DefaultAzureCredential` can use the signed-in Azure CLI account. No key is required. If configuration, identity, SDK or service access is unavailable, the application shows a notice and continues without speech.

`AZURE_STORAGE_ACCOUNT` and `AZURE_STORAGE_CONTAINER` are reserved for a future, explicitly approved retention requirement. They are currently unused to avoid collecting sensitive student information.

## Optional Azure OpenAI questions

| Variable | Purpose |
|---|---|
| `AZURE_OPENAI_ENDPOINT` | Custom endpoint for the Azure OpenAI resource |
| `AZURE_OPENAI_DEPLOYMENT` | Model deployment name; currently `question-generator` |
| `AZURE_OPENAI_API_VERSION` | API version; currently `2024-10-21` |

Assign the Container App managed identity the Cognitive Services OpenAI User role
on the Azure OpenAI resource. Generated output is schema-constrained and validated;
the app falls back to its reviewed local questions on any failure.
