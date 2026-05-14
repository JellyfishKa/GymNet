param(
    [switch]$NoBuild,
    [switch]$NoML,
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

function Test-NvidiaAvailable {
    $hasNvidiaCli = $null -ne (Get-Command "nvidia-smi" -ErrorAction SilentlyContinue)
    if (-not $hasNvidiaCli) {
        return $false
    }

    $runtimes = docker info --format "{{json .Runtimes}}"
    return $runtimes -match '"nvidia"'
}

$composeFile = "infra/docker-compose.yml"
$baseUp = if ($NoBuild) {
    "docker compose -f $composeFile up -d postgres backend frontend"
} else {
    "docker compose -f $composeFile up --build -d postgres backend frontend"
}

Invoke-Step -Title "Start base stack" -Command $baseUp

if (-not $NoML) {
    $useGpu = Test-NvidiaAvailable
    if ($useGpu) {
        Invoke-Step -Title "Run ML pipeline on GPU" -Command "docker compose -f $composeFile --profile ml-gpu run --rm ml-pipeline-gpu"
    } else {
        Invoke-Step -Title "Run ML pipeline on CPU" -Command "docker compose -f $composeFile run --rm ml-pipeline"
    }
}

Write-Host ""
Write-Host "Done."
Write-Host "Frontend: http://localhost:8080"
Write-Host "Backend health: http://localhost:8000/api/health"
