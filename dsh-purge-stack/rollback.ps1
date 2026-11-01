<#
  回退: 还原官方宿主, 可逆
  -Hard 同时清空本地注入层与供应商配置
#>
param([switch]$Hard)

$Home_   = "C:/Users/qq/.dsh"
$HostDir = "C:/Users/qq/AppData/Local/Programs/DeepSeek Harness"
$Res     = Join-Path $HostDir "resources"
$ts      = Get-Date -Format yyyyMMdd-HHmmss

Write-Host ""
Write-Host "=== 结束宿主 ===" -ForegroundColor Yellow
Get-Process | Where-Object { $_.ProcessName -match "DeepSeek Harness" } | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2
Write-Host "  已结束" -ForegroundColor Green

Write-Host ""
Write-Host "=== 还原 app.asar ===" -ForegroundColor Yellow
$disabled = @(Get-ChildItem $Res -Filter "app.asar.dshpurge-disabled-*" | Sort-Object LastWriteTime -Descending)
if ($disabled.Count -gt 0) {
  if (Test-Path (Join-Path $Res "app")) {
    Rename-Item (Join-Path $Res "app") ("app.disabled-" + $ts) -Force
    Write-Host ("  补丁版 app -> app.disabled-" + $ts)
  }
  Rename-Item $disabled[0].FullName "app.asar" -Force
  Write-Host ("  " + $disabled[0].Name + " -> app.asar") -ForegroundColor Green
} else {
  Write-Host "  未找到被移位的 app.asar, 跳过" -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "=== 还原 dsh.cmd ===" -ForegroundColor Yellow
$bin = Join-Path $Res "runtime\cli\bin"
$bak = @(Get-ChildItem $bin -Filter "dsh.cmd.bak-*" | Sort-Object LastWriteTime -Descending)
if ($bak.Count -gt 0) {
  Copy-Item $bak[0].FullName (Join-Path $bin "dsh.cmd") -Force
  Write-Host ("  已还原 " + $bak[0].Name) -ForegroundColor Green
} else { Write-Host "  无备份, 跳过" -ForegroundColor DarkGray }

Write-Host ""
Write-Host "=== 还原自动更新 ===" -ForegroundColor Yellow
$ubak = @(Get-ChildItem $Res -Filter "app-update.yml.bak-*" | Sort-Object LastWriteTime -Descending)
if ($ubak.Count -gt 0) {
  Copy-Item $ubak[0].FullName (Join-Path $Res "app-update.yml") -Force
  Write-Host ("  已还原 " + $ubak[0].Name) -ForegroundColor Green
} else { Write-Host "  无备份, 跳过" -ForegroundColor DarkGray }

if ($Hard) {
  Write-Host ""
  Write-Host "=== 清空本地注入层与供应商配置 ===" -ForegroundColor Yellow
  foreach ($f in @("prompt-inject.md", "personas.md")) {
    $p = Join-Path $Home_ $f
    if (Test-Path $p) { Move-Item $p ($p + ".off-" + $ts) -Force; Write-Host ("  " + $f + " 已移开") }
  }
  foreach ($p in @("desktop", "headless")) {
    $y = Join-Path $Home_ ("profiles\" + $p + "\cordis.patch.yml")
    if (Test-Path $y) {
      Copy-Item $y ($y + ".off-" + $ts) -Force
      [System.IO.File]::WriteAllText($y, "# cleared by rollback -Hard`n[]", (New-Object System.Text.UTF8Encoding($false)))
      Write-Host ("  " + $p + "\cordis.patch.yml 已清空")
    }
  }
}

Write-Host ""
Write-Host "完成. 重新打开 DeepSeek Harness 即为官方原版状态." -ForegroundColor Green
Write-Host "重新叠加: powershell -File C:/Users/qq/dsh-purge-stack/apply.ps1 -KillHost" -ForegroundColor Cyan
