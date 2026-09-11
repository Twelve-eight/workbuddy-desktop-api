@echo off
rem Foreground launcher for the WorkBuddy gateway (logs to console only).
rem Prefer gateway-window.cmd (visible status window with r/s/q controls).
chcp 65001 >nul
title WorkBuddy Gateway
cd /d "%~dp0"
set HOST=127.0.0.1
set PORT=8080
".venv\Scripts\python.exe" main.py