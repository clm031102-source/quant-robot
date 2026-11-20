@echo off
setlocal
cd /d "%~dp0.."
echo Quant Robot v2 — Local Research & Paper Trading Dashboard
echo Safety: Research-to-paper only (no broker, no live account, no live orders).
if not exist ".venv\Scripts\python.exe" (
  echo Missing .venv\Scripts\python.exe. Please create the Python 3.12 virtual environment first.
  pause
  exit /b 1
)
set PYTHONPATH=%cd%\src
".venv\Scripts\python.exe" scripts\run_dashboard.py --open
pause
