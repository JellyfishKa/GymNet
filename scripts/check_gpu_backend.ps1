# Quick check: backend Docker image uses GPU (not CPU-only torch).
$ErrorActionPreference = "Stop"
Write-Host "=== docker gpus ==="
docker inspect infra-backend-1 --format "DeviceRequests={{json .HostConfig.DeviceRequests}}"

Write-Host ""
Write-Host "=== torch in container ==="
docker exec infra-backend-1 python -c "import torch; print('version', torch.__version__); print('cuda', torch.cuda.is_available())"

Write-Host ""
Write-Host "=== /api/ml/status ==="
try {
  Invoke-RestMethod http://localhost:8000/api/ml/status |
    Select-Object inference_device, cuda_available, live_classification, model_exists |
    Format-List
} catch {
  Write-Host "backend not reachable on :8000"
}

Write-Host ""
Write-Host "Expected: cuda True, torch *+cu121*, backend image about 9 GB."
Write-Host "If cuda False: run scripts/restart_backend_gpu.ps1"
Write-Host "Do NOT run: docker compose -f infra/docker-compose.yml up without -f infra/docker-compose.gpu.yml"
