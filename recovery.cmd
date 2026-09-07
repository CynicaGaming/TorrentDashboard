@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 recovery_tool.py
) else (
  python recovery_tool.py
)
if errorlevel 1 pause
