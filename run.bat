@echo off
setlocal
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo No se encontro Python. Instalalo desde https://www.python.org/downloads/ y marca "Add python.exe to PATH".
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo Creando entorno virtual...
    python -m venv .venv
    if errorlevel 1 ( echo Error creando el entorno. & pause & exit /b 1 )
)

if not exist ".venv\.deps_v11_ok" (
    echo Instalando dependencias...
    ".venv\Scripts\python.exe" -m pip install --upgrade pip
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 ( echo Error instalando dependencias. & pause & exit /b 1 )
    echo ok> ".venv\.deps_v11_ok"
)

start "" ".venv\Scripts\pythonw.exe" drevo_light.py
endlocal
