@echo off
cd /d "%~dp0"
echo.
echo   Rollback to official stock host.
echo   Type Y and press Enter to confirm.
set /p ANS=
if /I not "%ANS%"=="Y" goto :eof
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0rollback.ps1"
echo.
pause
