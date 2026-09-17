param(
    [Parameter(Mandatory=$true)][string]$FunctionApp
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$stage = Join-Path ([System.IO.Path]::GetTempPath()) ("dyslexia-function-" + [guid]::NewGuid())
$tempRoot = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath())

try {
    New-Item -ItemType Directory -Path $stage | Out-Null
    Copy-Item -Path (Join-Path $repoRoot "azure_functions\*") -Destination $stage -Recurse
    $serviceTarget = Join-Path $stage "services"
    New-Item -ItemType Directory -Path $serviceTarget | Out-Null
    Copy-Item -Path (Join-Path $repoRoot "services\*.py") -Destination $serviceTarget
    Push-Location $stage
    func azure functionapp publish $FunctionApp --python
    if ($LASTEXITCODE -ne 0) { throw "Azure Function deployment failed." }
} finally {
    Pop-Location -ErrorAction SilentlyContinue
    $resolvedStage = [System.IO.Path]::GetFullPath($stage)
    if ($resolvedStage.StartsWith($tempRoot) -and (Test-Path -LiteralPath $resolvedStage)) {
        Remove-Item -LiteralPath $resolvedStage -Recurse
    }
}
