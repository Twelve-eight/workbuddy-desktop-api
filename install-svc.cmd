@echo off
setlocal
rem One-click install: place a visible status-window launcher in the user
rem Startup folder and open the window right now. No admin needed.
set STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
set DEST=%STARTUP%\WorkBuddyGateway.cmd

> "%DEST%" echo @echo off
>> "%DEST%" echo cd /d "%~dp0"
>> "%DEST%" echo call gateway-window.cmd

if errorlevel 1 (
  echo Failed to write Startup launcher.
  exit /b 1
)
start "" "%DEST%"
echo Installed: visible status window opens now and at every logon.
echo Commands inside window: r=restart  s=stop  c=clear  q=quit
echo Status endpoint: http://127.0.0.1:8080/v1/models