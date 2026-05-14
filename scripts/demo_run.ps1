$ErrorActionPreference = "Stop"

Write-Host "Starting GymNet demo services..."
Write-Host "1) Start PostgreSQL via docker-compose"
Write-Host "2) Start backend: uvicorn app.main:app --reload --port 8000"
Write-Host "3) Start frontend: npm run dev"

Write-Host ""
Write-Host "Commands:"
Write-Host "docker compose -f infra/docker-compose.yml up -d"
Write-Host "cd backend; pip install -r requirements.txt; uvicorn app.main:app --reload --port 8000"
Write-Host "cd frontend; npm install; npm run dev"
