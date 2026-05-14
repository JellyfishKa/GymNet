$ErrorActionPreference = "Stop"

Write-Host "Запуск GymNet через Docker..."
Write-Host "1) Собрать и поднять контейнеры"
Write-Host "2) Открыть frontend в браузере"
Write-Host "3) Проверить backend health"
Write-Host "4) Опционально запустить клиент веб-камеры"

Write-Host ""
Write-Host "Команды:"
Write-Host "docker compose -f infra/docker-compose.yml up --build -d"
Write-Host "start http://localhost:8080"
Write-Host "start http://localhost:8000/api/health"
Write-Host "python scripts/camera_ws_client.py"
