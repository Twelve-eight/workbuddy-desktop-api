@echo off
rem Visible status window + restart controller for the WorkBuddy gateway.
rem Commands inside the window: r=restart  s=stop  c=clear  q=quit
chcp 65001 >nul
title WorkBuddy Gateway - status window
cd /d "%~dp0"
set HOST=127.0.0.1
set PORT=8080
".venv\Scripts\python.exe" supervisor.py
pause