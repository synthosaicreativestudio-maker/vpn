@echo off
title RBN Bot Auto-Restart
:start
cd /d "%~dp0"
echo [%date% %time%] Starting RBN Bot...
python main.py
echo [%date% %time%] Bot crashed or stopped. Restarting in 5 seconds...
timeout /t 5
goto start
