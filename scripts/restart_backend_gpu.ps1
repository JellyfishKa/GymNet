# Пересоздать backend с GPU overlay (не использовать docker-compose.yml без -f gpu).
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

Write-Host "GPU backend: compose + force-recreate..."
docker compose -f infra/docker-compose.yml -f infra/docker-compose.gpu.yml up -d --build --force-recreate backend

Write-Host ""
Write-Host "Проверка CUDA в контейнере:"
docker exec infra-backend-1 python -c "import torch; print('torch', torch.__version__); print('cuda', torch.cuda.is_available())"

Write-Host ""
Write-Host "ML status: http://localhost:8000/api/ml/status"
