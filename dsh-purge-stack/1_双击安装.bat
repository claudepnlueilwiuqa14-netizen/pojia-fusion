@echo off
cd /d "%~dp0"
echo.
echo   dsh-purge-stack  one-click install
echo   ---------------------------------
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0apply.ps1" -KillHost
echo.
echo   If the host is open, close it fully (tray too) and reopen.
echo.
pause
