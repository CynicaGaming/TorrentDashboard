@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py dashboard.py
  goto :end
)
where python >nul 2>nul
if %errorlevel%==0 (
  python dashboard.py
  goto :end
)
echo.
echo Python 3 was not found.
echo Install Python 3, then run this file again.
echo.
pause
:end
endlocal
