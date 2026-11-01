# install_all.ps1 —— 把《DSH 插件下载榜横评》里的插件一次性装进 SDzibo（profile=desktop）
# 用法: powershell -ExecutionPolicy Bypass -File install_all.ps1
# 前置: 已启动 SDzibo，且 dsh CLI 在 PATH（否则自动回退到 npx -y @deepseek-ai/dsh）
param(
  [string]$Profile = "desktop",
  [switch]$SkipGitHubSource
)

$ErrorActionPreference = "Continue"

# 第一档：下载榜 7 款（npm 源）
$NPM = @(
  "billion-context", "dshmarket", "dsh-codex-ui", "dsh-better-sidebar",
  "dsh-free-search", "dsh-ops", "dsh-git-graph",
  "dsh-web-ui", "dsh-TUI", "modlens", "dsh-vision-toolkit",
  "ModSearch", "dsh-workflow", "dsh-deep-whale", "dsh-chat-import", "dsh-find-plugin"
)
# 第二档：github 源
$GH = @(
  "github:NanniCoder/dsh-agent-teams", "github:myllulling/dsh-image-gen",
  "github:zhulyueya/dsh-im-gateway", "github:Anionex/dsh-vision-toolkit",
  "github:HindsightRepo/Hindsight", "github:archify/archify"
)

function Resolve-Dsh {
  if (Get-Command dsh -ErrorAction SilentlyContinue) { return "dsh" }
  return "npx -y @deepseek-ai/dsh dsh"
}

$DSH = Resolve-Dsh
$all = $NPM
if (-not $SkipGitHubSource) { $all += $GH }

$ok = @(); $fail = @()
foreach ($p in $all) {
  Write-Host "`n>>> 安装 $p ..." -ForegroundColor Cyan
  try {
    $out = & cmd /c "$DSH plugin --profile $Profile add $p" 2>&1 | Out-String
    if ($LASTEXITCODE -eq 0 -and $out -notmatch "error|失败|not found") {
      Write-Host "    ✅ $p 成功" -ForegroundColor Green; $ok += $p
    } else {
      Write-Host "    ⚠️ $p 失败: $($out.Trim().Split([Environment]::NewLine)[0])" -ForegroundColor Yellow; $fail += $p
    }
  } catch {
    Write-Host "    ⚠️ $p 异常: $_" -ForegroundColor Yellow; $fail += $p
  }
}

Write-Host "`n================ 汇总 ================"
Write-Host "成功 $($ok.Count): $($ok -join ', ')"
Write-Host "失败 $($fail.Count): $($fail -join ', ')"
if ($fail.Count) {
  Write-Host "`n失败项可手动重试，或换 github: 形式 / 在 SDzibo 插件页直接搜名字装。"
}
