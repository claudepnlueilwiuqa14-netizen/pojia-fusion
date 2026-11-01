@echo off
cd /d "%~dp0"
echo.
echo   Running live chain test (9 checks)...
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0verify.ps1"
echo.
pause
