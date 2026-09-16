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
| `AZURE_SPEECH_ENDPOINT` | Speech resource endpoint |
| `AZURE_SPEECH_RESOURCE_ID` | Full Azure resource ID used for Entra authentication |
| `AZURE_SPEECH_LANGUAGE` | Recognition locale; defaults to `en-US` |

Assign the Container App managed identity the Cognitive Services User role on the Speech resource. Locally, `DefaultAzureCredential` can use the signed-in Azure CLI account. No key is required. If configuration, identity, SDK or service access is unavailable, the application shows a notice and continues without speech.

`AZURE_STORAGE_ACCOUNT` and `AZURE_STORAGE_CONTAINER` are reserved for a future, explicitly approved retention requirement. They are currently unused to avoid collecting sensitive student information.
