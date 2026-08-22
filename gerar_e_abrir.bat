@echo off
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Instalando dependencias na primeira vez...
    python -m venv .venv
    ".venv\Scripts\python.exe" -m pip install -q -r requirements.txt
)

".venv\Scripts\python.exe" gerar_painel.py
start "" "docs\index.html"
