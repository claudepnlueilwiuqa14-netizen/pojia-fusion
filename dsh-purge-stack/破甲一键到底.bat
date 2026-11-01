@echo off
chcp 65001 >nul
title 破甲一键到底 (DeepSeek Harness)
set "PY=C:\Users\qq\AppData\Local\Programs\Python\Python313\python.exe"
set "SCRIPT=C:\Users\qq\dsh-purge-stack\master_once.py"

echo ============================================
echo   破甲一键到底
echo   自提权 ^| 幂等 ^| 守护常驻 ^| 落盘强校验
echo ============================================
echo 脚本: %SCRIPT%
echo 会出现 UAC 窗口，点「是」。
echo.

powershell -NoProfile -Command "Start-Process -FilePath '%PY%' -ArgumentList '%SCRIPT%' -Verb RunAs -Wait"

echo.
echo 完成。日志: C:\Users\qq\dsh-purge-stack\master_once.log
echo.
pause
