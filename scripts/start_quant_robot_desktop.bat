@echo off
setlocal
cd /d "%~dp0.."
echo Quant Robot desktop launcher (research-to-paper only; no broker/account/order/live trading).
python scripts\run_desktop_app.py
pause
