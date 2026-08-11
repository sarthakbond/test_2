@echo off
setlocal

set "ROOT=%~dp0"
set "PYTHON=python"

"%PYTHON%" --version >nul 2>&1
if errorlevel 1 (
    echo Python was not found.
    pause
    exit /b 1
)

"%PYTHON%" -c "import fastapi, cv2, tensorflow, torch, faiss, deepface, retinaface, tf_keras, transformers" >nul 2>&1
if errorlevel 1 (
    echo Backend dependencies are missing. Installing them for Python 3.11...
    "%PYTHON%" -m pip install -r "%ROOT%requirements.txt"
    if errorlevel 1 (
        echo Backend dependency installation failed.
        pause
        exit /b 1
    )
)

if not exist "%ROOT%frontend\node_modules" (
    echo Frontend dependencies are missing. Installing them...
    cd /d "%ROOT%frontend"
    call npm.cmd install
    if errorlevel 1 (
        echo Frontend dependency installation failed.
        pause
        exit /b 1
    )
    cd /d "%ROOT%"
)

start "SWARAKSHA Backend" /D "%ROOT%" cmd /k ""%PYTHON%" -m uvicorn api.main:app --reload --host 127.0.0.1 --port 8000"
start "SWARAKSHA Frontend" /D "%ROOT%frontend" cmd /k npm.cmd run dev -- --host 127.0.0.1

echo SWARAKSHA v2 started.
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:5173
endlocal
