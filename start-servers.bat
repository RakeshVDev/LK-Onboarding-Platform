@echo off
echo ========================================================
echo   Starting ASE Onboarding Platform Services
echo ========================================================

cd /d "%~dp0"

echo [1/3] Starting Identity Service on port 8000...
start "ASE Identity Service (Port 8000)" cmd /k "cd /d backend && set PYTHONPATH=%cd% && .venv\Scripts\activate.bat && python -m uvicorn services.identity.app.main:app --host 127.0.0.1 --port 8000 --reload"

echo [2/3] Starting Training Service on port 8001...
start "ASE Training Service (Port 8001)" cmd /k "cd /d backend && set PYTHONPATH=%cd% && .venv\Scripts\activate.bat && python -m uvicorn services.training.app.main:app --host 127.0.0.1 --port 8001 --reload"

echo [3/3] Starting Frontend Dev Server on port 4200...
start "ASE Angular Frontend (Port 4200)" cmd /k "cd /d frontend && npm start"

echo.
echo ========================================================
echo All 3 services are launching in separate windows:
echo - Identity:  http://127.0.0.1:8000/docs
echo - Training:  http://127.0.0.1:8001/docs
echo - Frontend:  http://localhost:4200/
echo ========================================================
pause

