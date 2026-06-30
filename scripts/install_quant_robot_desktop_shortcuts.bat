@echo off
setlocal
cd /d "%~dp0.."
echo Quant Robot shortcut installer (research-to-paper only; no broker/account/order/live trading).
python scripts\install_quant_robot_desktop_shortcuts.py --repo-root "%CD%"
pause
