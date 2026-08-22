@echo off
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Instalando dependencias na primeira vez...
    python -m venv .venv
    ".venv\Scripts\python.exe" -m pip install -q -r requirements.txt
)

start "CaptaGov (fecha essa janela pra parar o servidor)" ".venv\Scripts\python.exe" -m flask --app app run --no-debugger --no-reload

timeout /t 3 /nobreak >nul
start "" "http://127.0.0.1:5000"
