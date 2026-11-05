# Start all ASE Onboarding Platform services
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  Starting ASE Onboarding Platform Services" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan

# 1. Identity Service
Write-Host "[1/3] Starting Identity Service on port 8000..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$scriptDir\backend'; `$env:PYTHONPATH = (Get-Location).Path; .\`.venv\Scripts\Activate.ps1; python -m uvicorn services.identity.app.main:app --host 127.0.0.1 --port 8000 --reload"

# 2. Training Service
Write-Host "[2/3] Starting Training Service on port 8001..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$scriptDir\backend'; `$env:PYTHONPATH = (Get-Location).Path; .\`.venv\Scripts\Activate.ps1; python -m uvicorn services.training.app.main:app --host 127.0.0.1 --port 8001 --reload"

# 3. Angular Frontend
Write-Host "[3/3] Starting Frontend Dev Server on port 4200..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$scriptDir\frontend'; npm start"

Write-Host "`nAll 3 services are launching in separate windows:" -ForegroundColor Yellow
Write-Host "  - Identity Service:  http://127.0.0.1:8000/docs" -ForegroundColor White
Write-Host "  - Training Service:  http://127.0.0.1:8001/docs" -ForegroundColor White
Write-Host "  - Angular Frontend:  http://localhost:4200/" -ForegroundColor White
Write-Host "========================================================`n" -ForegroundColor Cyan

