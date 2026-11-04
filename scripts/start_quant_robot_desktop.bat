@echo off
setlocal
cd /d "%~dp0.."
echo Quant Robot desktop launcher (research-to-paper only; no broker/account/order/live trading).
if not exist ".venv\Scripts\python.exe" (
  echo Project Python environment is missing. Restore the verified project environment first.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" scripts\run_desktop_app.py --page dashboard --target-id ordinary-daily-action-card
pause
