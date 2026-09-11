@echo off
rem WorkBuddy desktop gateway - standalone launcher
rem Starts the OpenAI-compatible gateway for local WorkBuddy free models.
rem Usage: double-click, or run via Task Scheduler at logon.
set HOST=127.0.0.1
set PORT=8080
cd /d "%~dp0"
".venv\Scripts\python.exe" main.py