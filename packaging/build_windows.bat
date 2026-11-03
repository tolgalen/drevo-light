@echo off
rem Build dist\drevo-light\drevo-light.exe (needs Python 3.9+). Optional: Inno Setup for the installer.
setlocal
cd /d "%~dp0\.."
if not exist ".venv\Scripts\python.exe" python -m venv .venv
".venv\Scripts\python.exe" -m pip install -q -r requirements.txt pyinstaller
".venv\Scripts\pyinstaller.exe" packaging\drevo-light.spec --noconfirm
where iscc >nul 2>nul && iscc packaging\drevo-light.iss
echo Done: dist\drevo-light\drevo-light.exe
endlocal
