@echo off
chcp 65001 >nul
title 破甲救急 - 一键自愈
cd /d "C:/Users/qq/dsh-purge-stack"

echo [1/4] 结束旧代理与守护...
for /f "tokens=5" %%p in ('netstat -ano ^| findstr "LISTENING" ^| findstr ":8787"') do (
  taskkill /F /PID %%p >nul 2>&1
)
taskkill /F /IM pythonw.exe /FI "WINDOWTITLE eq *supervisor*" >nul 2>&1

echo [2/4] 用 explorer 拉起 supervisor (挂在用户会话, 不会随别的工作区掉)...
start "" explorer.exe "C:/Users/qq/dsh-purge-stack/proxy/dsh_pojia_supervisor.vbs"
start "" explorer.exe "C:/Users/qq/dsh-purge-stack/proxy/dsh_relay_proxy.vbs"
start "" explorer.exe "C:/Users/qq/AppData/Roaming/Microsoft/Windows/Start Menu/Programs/Startup/dsh_pojia_guardian.vbs"

echo [3/4] 等待代理就绪...
set /a n=0
:wait
timeout /t 2 /nobreak >nul
set /a n+=1
curl -s -m 3 http://127.0.0.1:8787/health >nul 2>&1 && goto ok
if %n% lss 15 goto wait
echo     !! 代理 30 秒内没起来, 看 proxy\crash.log 与 proxy\proxy_stderr.log
pause
exit /b 1

:ok
echo [4/4] 自愈完成.
echo.
echo   代理健康: http://127.0.0.1:8787/health
echo   模型列表: http://127.0.0.1:8787/v1/models
echo   崩溃日志: C:/Users/qq/dsh-purge-stack/proxy/crash.log
echo.
pause
