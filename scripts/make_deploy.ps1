# make_deploy.ps1 — 生成 Linux 友好的部署包 Quick_Sparam_deploy_<日期>.tar.gz
#
# 用法：
#   .\scripts\make_deploy.ps1                 # 生成到工程根目录
#   .\scripts\make_deploy.ps1 -Output D:\out  # 指定输出目录
#   .\scripts\make_deploy.ps1 -Format zip     # 改用 zip 格式（Windows 默认双击可解）
#
# 设计：白名单制——只把"打包/安装必需 + 用户使用指南"打进去。
# 排除的内容（即使白名单目录下也跳过）：.venv/、__pycache__/、*.pyc、build/、dist/、
#   build-linux/、dist-linux/、.pytest_cache/、samples/、picture/、docs/archive/、
#   docs/ppt_assets/、docs/generate_*.py、docs/todolist.md、Public/data_feedback/、
#   *.rar、importtime_*.txt
#
# 公司 Linux 端解开后的 README：
#   tar -xzf Quick_Sparam_deploy_*.tar.gz
#   cd Quick_Sparam
#   python3.11 -m venv .venv && source .venv/bin/activate
#   pip install -r packaging/linux/requirements-linux.txt
#   pyinstaller --noconfirm Quick_Sparam_linux.spec
#   # 产物在 dist/Quick_Sparam/Quick_Sparam

[CmdletBinding()]
param(
    [string]$Output = $null,
    [ValidateSet('tar.gz', 'zip')]
    [string]$Format = 'tar.gz'
)

$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not $Output) { $Output = $Root }
if (-not (Test-Path $Output)) { New-Item -ItemType Directory -Path $Output | Out-Null }

# --- 白名单：要带进包的顶层路径 ---
$Include = @(
    # 入口与核心模块
    'Quick_Sparam_B.py',
    'Quick_Sparam_install.pyw',
    'app_utils.py',
    'main_window.py',
    'sparam_core.py',
    # 领域 / 服务 / 基础设施 / UI / 运行时
    'QS_domain',
    'QS_services',
    'QS_infra',
    'QS_dialogs',
    'QS_runtime_services',
    # 资源与打包配置
    'resources',
    'pyinstaller_hooks',
    'packaging',
    'requirements.txt',
    'Quick_Sparam_install.spec',
    'Quick_Sparam_linux.spec',
    'build_linux.ps1',
    'scripts',
    # 单元测试（用户选择带上）
    'tests',
    # 元信息 / 文档（精选）
    'CLAUDE.md',
    'AGENTS.md',
    '.gitignore',
    'docs\AGENT_GUIDE.md',
    'docs\ARCHITECTURE.md',
    'docs\CONVENTIONS.md',
    'docs\INTERFACES.md',
    'docs\Quick_Sparam_使用指南.html',
    'docs\Quick_Sparam_功能介绍与使用指南.pptx'
)

# --- 排除模式（tar 用，在白名单目录里再次过滤）---
$Excludes = @(
    '__pycache__',
    '*.pyc', '*.pyo', '*.pyd',
    '.pytest_cache', '.mypy_cache', '.ruff_cache',
    '.idea', '.codexbridge', '.venv',
    'build', 'dist', 'build-linux', 'dist-linux',
    'importtime_*.txt'
)

$Date = Get-Date -Format 'yyyyMMdd'
$Stem = "Quick_Sparam_deploy_$Date"
$Archive = Join-Path $Output "$Stem.$Format"

# --- 1. 复制到临时目录（白名单） ---
$Staging = Join-Path $env:TEMP "qs_deploy_$Date"
if (Test-Path $Staging) { Remove-Item -Recurse -Force $Staging }
$StagingRoot = Join-Path $Staging 'Quick_Sparam'
New-Item -ItemType Directory -Path $StagingRoot | Out-Null

Write-Host "[1/3] 收集白名单文件到 $StagingRoot" -ForegroundColor Cyan
foreach ($item in $Include) {
    $src = Join-Path $Root $item
    if (-not (Test-Path $src)) {
        Write-Host "  ! 缺失（跳过）：$item" -ForegroundColor Yellow
        continue
    }
    $dst = Join-Path $StagingRoot $item
    $dstParent = Split-Path -Parent $dst
    if (-not (Test-Path $dstParent)) { New-Item -ItemType Directory -Path $dstParent -Force | Out-Null }

    if ((Get-Item $src).PSIsContainer) {
        # 目录：用 robocopy 过滤排除
        $excludeDirs  = $Excludes | Where-Object { -not $_.Contains('.') }
        $excludeFiles = $Excludes | Where-Object {     $_.Contains('.') }
        $args = @($src, $dst, '/E', '/NFL', '/NDL', '/NJH', '/NJS', '/NP', '/NS')
        if ($excludeDirs)  { $args += '/XD'; $args += $excludeDirs }
        if ($excludeFiles) { $args += '/XF'; $args += $excludeFiles }
        & robocopy @args | Out-Null
        # robocopy 退出码 <8 都视为成功
        if ($LASTEXITCODE -ge 8) { throw "robocopy 复制 $item 失败 (exit $LASTEXITCODE)" }
    } else {
        Copy-Item $src $dst -Force
    }
}

# --- 2. 打包 ---
Write-Host "[2/3] 打包 → $Archive" -ForegroundColor Cyan
if (Test-Path $Archive) { Remove-Item -Force $Archive }

if ($Format -eq 'zip') {
    Compress-Archive -Path "$StagingRoot" -DestinationPath $Archive -CompressionLevel Optimal
} else {
    # Windows 10+ 自带 tar.exe（基于 libarchive）
    & tar.exe -czf $Archive -C $Staging 'Quick_Sparam'
    if ($LASTEXITCODE -ne 0) { throw "tar 失败 (exit $LASTEXITCODE)" }
}

# --- 3. 清临时区 ---
Remove-Item -Recurse -Force $Staging

$Size = [math]::Round((Get-Item $Archive).Length / 1MB, 1)
Write-Host "`n[OK] 产物：$Archive  ($Size MB)" -ForegroundColor Green
Write-Host "[OK] 公司 Linux 端解开后：" -ForegroundColor Green
Write-Host "       tar -xzf $(Split-Path -Leaf $Archive)" -ForegroundColor Gray
Write-Host "       cd Quick_Sparam" -ForegroundColor Gray
Write-Host "       python3.11 -m venv .venv && source .venv/bin/activate" -ForegroundColor Gray
Write-Host "       pip install -r packaging/linux/requirements-linux.txt" -ForegroundColor Gray
Write-Host "       pyinstaller --noconfirm Quick_Sparam_linux.spec" -ForegroundColor Gray
