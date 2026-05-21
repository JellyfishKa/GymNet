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

$composeFile = "infra/docker-compose.yml"
$baseUp = if ($NoBuild) {
    "docker compose -f $composeFile up -d postgres backend frontend ml-autotrain"
} else {
    "docker compose -f $composeFile up --build -d postgres backend frontend ml-autotrain"
}

Invoke-Step -Title "Start base stack" -Command $baseUp

if (-not $NoML) {
    Invoke-Step -Title "Run ML pipeline (profile ml)" -Command "docker compose -f $composeFile --profile ml run --rm ml-pipeline"
}

Write-Host ""
Write-Host "Done."
Write-Host "Frontend: http://localhost:8080"
Write-Host "Backend health: http://localhost:8000/api/health"
