@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (py dashboard.py & goto :end)
where python >nul 2>nul
if %errorlevel%==0 (python dashboard.py & goto :end)
echo Python 3 was not found. Install Python 3 and try again.
pause
:end
endlocal
