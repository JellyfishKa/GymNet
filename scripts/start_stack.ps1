param(
    [switch]$NoBuild,
    [switch]$NoML,
    [switch]$Gpu,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

function Invoke-Step {
    param(
        [string]$Title,
        [string]$Command
    )

    Write-Host ""
    Write-Host "== $Title =="
    Write-Host $Command

    if (-not $DryRun) {
        Invoke-Expression $Command
    }
}

$composeFile = "infra/docker-compose.yml"
$composeGpu = "infra/docker-compose.gpu.yml"
$composeArgs = if ($Gpu) { "-f $composeFile -f $composeGpu" } else { "-f $composeFile" }
$buildFlag = if ($NoBuild) { "" } else { " --build" }
$baseUp = "docker compose $composeArgs up$buildFlag -d postgres backend frontend ml-autotrain"

Invoke-Step -Title "Start base stack" -Command $baseUp

if (-not $NoML) {
    $mlCompose = if ($Gpu) { "-f $composeFile -f $composeGpu" } else { "-f $composeFile" }
    Invoke-Step -Title "Run ML pipeline (profile ml)" -Command "docker compose $mlCompose --profile ml run --rm ml-pipeline"
}

Write-Host ""
Write-Host "Done."
Write-Host "Frontend: http://localhost:8080"
Write-Host "Backend health: http://localhost:8000/api/health"
Write-Host "ML device: http://localhost:8000/api/ml/status (inference_device, cuda_available)"
if ($Gpu) {
    Write-Host "GPU overlay: ON (backend PyTorch cu121, gpus: all)"
}
