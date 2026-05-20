# clean_workspace.ps1 — 清理本机工作区里的临时产物 / 缓存
#
# 用法：
#   .\scripts\clean_workspace.ps1            # 实际执行
#   .\scripts\clean_workspace.ps1 -DryRun    # 只列要删的内容，不动手
#
# 删除范围：
#   - PyInstaller 产物：dist/、build/、dist-linux/、build-linux/
#   - Python 缓存：所有 __pycache__/（递归）、.pytest_cache/、.mypy_cache/、.ruff_cache/
#   - AI 工具本地缓存：.codexbridge/、.claude/settings.local.json
#   - 运行时反馈数据：Public/data_feedback/inbox/（含隐私 JSON，应当定期清掉）
#   - 性能日志：importtime_*.txt

[CmdletBinding()]
param([switch]$DryRun)

$ErrorActionPreference = 'Stop'

# 锚定到工程根（脚本所在目录的上一级）
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Get-DirSize([string]$path) {
    if (-not (Test-Path $path)) { return 0 }
    return ((Get-ChildItem $path -Recurse -Force -ErrorAction SilentlyContinue |
             Measure-Object Length -Sum).Sum)
}

function Remove-Target([string]$path) {
    if (-not (Test-Path $path)) { return 0 }
    $size = Get-DirSize $path
    $mb = [math]::Round($size / 1MB, 2)
    if ($DryRun) {
        Write-Host "[dry-run] would remove $path  ($mb MB)" -ForegroundColor Yellow
    } else {
        Write-Host "remove $path  ($mb MB)" -ForegroundColor Cyan
        Remove-Item -Recurse -Force $path
    }
    return $size
}

$total = 0

# --- 1. 大件产物 ---
foreach ($t in 'dist', 'build', 'dist-linux', 'build-linux') {
    $total += Remove-Target $t
}

# --- 2. 顶层缓存目录 ---
foreach ($t in '.pytest_cache', '.mypy_cache', '.ruff_cache', '.codexbridge') {
    $total += Remove-Target $t
}

# --- 3. 递归清 __pycache__ ---
$pycaches = Get-ChildItem -Path . -Filter '__pycache__' -Recurse -Directory -Force -ErrorAction SilentlyContinue
foreach ($p in $pycaches) {
    $total += Remove-Target $p.FullName
}

# --- 4. 运行时反馈数据（隐私敏感）---
$total += Remove-Target 'Public\data_feedback\inbox'

# --- 5. 杂项 ---
$localSettings = '.claude\settings.local.json'
if (Test-Path $localSettings) {
    $total += Remove-Target $localSettings
}
$importTimeFiles = Get-ChildItem -Path . -Filter 'importtime_*.txt' -File -ErrorAction SilentlyContinue
foreach ($f in $importTimeFiles) {
    $total += Remove-Target $f.FullName
}

$totalMb = [math]::Round($total / 1MB, 1)
$prefix = if ($DryRun) { '预计可回收' } else { '已回收' }
Write-Host "`n$prefix : $totalMb MB" -ForegroundColor Green
