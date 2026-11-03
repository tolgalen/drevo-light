@echo off
rem Remove everything that should not be committed (venv, caches, build output).
cd /d "%~dp0"
for %%d in (.venv venv env build dist .pytest_cache .mypy_cache .ruff_cache .tox htmlcov) do (
  if exist "%%d" rmdir /s /q "%%d" && echo removed: %%d
)
for /d /r %%d in (__pycache__) do if exist "%%d" rmdir /s /q "%%d"
for /d %%d in (*.egg-info) do rmdir /s /q "%%d"
del /s /q *.pyc *.pyo *.log 2>nul
echo Done.
