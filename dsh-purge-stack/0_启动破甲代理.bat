@echo off
chcp 65001 >nul
set PY=C:\Users\qq\AppData\Local\Programs\Python\Python313\pythonw.exe
set SRC=C:\Users\qq\dsh-purge-stack\proxy\dsh_relay_proxy.py

echo [1/2] 检测代理是否已在运行...
powershell -NoProfile -Command "try{$r=Invoke-RestMethod -Uri 'http://127.0.0.1:8787/health' -TimeoutSec 3; if($r.ok){exit 0}else{exit 1}}catch{exit 1}"
if %ERRORLEVEL%==0 (
  echo       代理已在运行
) else (
  echo       未运行, 正在启动...
  start "" "%PY%" "%SRC%"
  timeout /t 2 >nul
)

echo [2/2] 安装开机自启...
copy /Y "C:\Users\qq\dsh-purge-stack\proxy\dsh_relay_proxy.vbs" "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\dsh_relay_proxy.vbs" >nul
echo       已写入启动目录

echo.
echo 代理地址: http://127.0.0.1:8787/v1
pause
