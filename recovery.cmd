@echo off
setlocal
cd /d "%~dp0"
if exist "Recovery.exe" (
  "Recovery.exe" %*
  exit /b %errorlevel%
)
set "PYTHONPATH=%~dp0src;%PYTHONPATH%"
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 -m torrent_dashboard.recovery_tool %*
) else (
  python -m torrent_dashboard.recovery_tool %*
)
