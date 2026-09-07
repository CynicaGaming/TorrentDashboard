@echo off
setlocal
cd /d "%~dp0"
if exist "Recovery.exe" (
  "Recovery.exe" %*
  exit /b %errorlevel%
)
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 recovery_tool.py %*
) else (
  python recovery_tool.py %*
)
