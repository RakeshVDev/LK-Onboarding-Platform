@echo off
echo ========================================================
echo   Starting LK Onboarding Platform Services
echo ========================================================

cd /d "%~dp0"

echo [1/3] Starting Identity Service on port 8001...
start "LK Identity Service (Port 8001)" /D "%~dp0backend" cmd /k "set PYTHONPATH=%~dp0backend&& .venv\Scripts\python.exe -m uvicorn services.identity.app.main:app --host 127.0.0.1 --port 8001 --reload"

echo [2/3] Starting Training Service on port 8002...
start "LK Training Service (Port 8002)" /D "%~dp0backend" cmd /k "set PYTHONPATH=%~dp0backend&& .venv\Scripts\python.exe -m uvicorn services.training.app.main:app --host 127.0.0.1 --port 8002 --reload"

echo [3/3] Starting Frontend Dev Server on port 4200...
start "LK Angular Frontend (Port 4200)" /D "%~dp0frontend" cmd /k "npm start"

echo.
echo ========================================================
echo All 3 services are launching in separate windows:
echo   - Identity:  http://127.0.0.1:8001/docs
echo   - Training:  http://127.0.0.1:8002/docs
echo   - Frontend:  http://localhost:4200/
echo ========================================================
