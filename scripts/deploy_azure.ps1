param(
    [Parameter(Mandatory=$true)][string]$ResourceGroup,
    [Parameter(Mandatory=$true)][string]$AppName,
    [string]$Location = "centralindia",
    [string]$Environment
)

$ErrorActionPreference = "Stop"
az account show --output table
if ($LASTEXITCODE -ne 0) { throw "Azure CLI authentication failed." }

if (-not (az group exists --name $ResourceGroup | ConvertFrom-Json)) {
    az group create --name $ResourceGroup --location $Location --output table
    if ($LASTEXITCODE -ne 0) { throw "Resource group creation failed." }
}

$upArgs = @(
    "containerapp", "up",
    "--name", $AppName,
    "--resource-group", $ResourceGroup,
    "--location", $Location,
    "--source", ".",
    "--ingress", "external",
    "--target-port", "8501"
)
if ($Environment) { $upArgs += @("--environment", $Environment) }
az @upArgs
if ($LASTEXITCODE -ne 0) { throw "Container App deployment failed." }

az containerapp update `
    --name $AppName `
    --resource-group $ResourceGroup `
    --cpu 0.5 `
    --memory 1Gi `
    --min-replicas 0 `
    --max-replicas 1 `
    --output none
if ($LASTEXITCODE -ne 0) { throw "Container App resource update failed." }

$fqdn = az containerapp show --name $AppName --resource-group $ResourceGroup --query properties.configuration.ingress.fqdn -o tsv
if ($LASTEXITCODE -ne 0) { throw "Could not read the deployed endpoint." }
Write-Host "Deployed: https://$fqdn"
