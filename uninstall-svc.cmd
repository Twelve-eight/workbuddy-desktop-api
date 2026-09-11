@echo off
setlocal
rem One-click uninstall: remove the WorkBuddyGateway autostart entry
rem (both the new .cmd window entry and any legacy .vbs entry).
set STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
del /Q "%STARTUP%\WorkBuddyGateway.cmd" >nul 2>&1
del /Q "%STARTUP%\WorkBuddyGateway.vbs" >nul 2>&1
echo Autostart entry removed (running gateway window is left as-is).