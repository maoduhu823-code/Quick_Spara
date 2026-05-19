# build_linux.ps1 — 在 Windows 上一键打包 Linux 版 Quick_Sparam
#
# 前置：
#   1. 已装 Docker Desktop 并启动
#   2. 代码已从 PyQt6 迁移到 PyQt5（PyQt6 wheel 不兼容 glibc 2.17）
#
# 用法：
#   .\build_linux.ps1                # 完整构建（含 docker build）
#   .\build_linux.ps1 -SkipBuild     # 跳过镜像构建（镜像已存在时加速）
#   .\build_linux.ps1 -Shell         # 进入容器交互 shell，手动调试
#
# 产物：dist-linux/Quick_Sparam/ —— 整个目录拷到目标服务器即可运行
#   ./Quick_Sparam   # 启动可执行入口

[CmdletBinding()]
param(
    [switch]$SkipBuild,
    [switch]$Shell
)

$ErrorActionPreference = 'Stop'

$ImageTag = 'quicksparam-builder:manylinux2014'
$ProjectRoot = $PSScriptRoot
$Dockerfile = Join-Path $ProjectRoot 'packaging\linux\Dockerfile'

if (-not (Test-Path $Dockerfile)) {
    throw "找不到 Dockerfile: $Dockerfile"
}

# --- 1. 构建镜像 ---
if (-not $SkipBuild) {
    Write-Host "[1/3] docker build → $ImageTag" -ForegroundColor Cyan
    docker build -f $Dockerfile -t $ImageTag $ProjectRoot
    if ($LASTEXITCODE -ne 0) { throw "docker build 失败" }
} else {
    Write-Host "[1/3] 跳过 docker build (--SkipBuild)" -ForegroundColor Yellow
}

# --- 2. 清理上次产物 ---
$DistDir = Join-Path $ProjectRoot 'dist-linux'
$BuildDir = Join-Path $ProjectRoot 'build-linux'
foreach ($d in @($DistDir, $BuildDir)) {
    if (Test-Path $d) {
        Write-Host "[2/3] 清理旧目录 $d" -ForegroundColor Cyan
        Remove-Item -Recurse -Force $d
    }
}

# --- 3. 跑容器 ---
# Docker on Windows 接受 /src 风格的容器路径；Windows 路径需转换为 docker 形式
$MountSrc = $ProjectRoot -replace '\\', '/'

if ($Shell) {
    Write-Host "[3/3] 进入容器 shell (Ctrl+D 退出)" -ForegroundColor Cyan
    docker run --rm -it `
        -v "${MountSrc}:/src" `
        -w /src `
        --entrypoint /bin/bash `
        $ImageTag
} else {
    Write-Host "[3/3] 容器内执行 pyinstaller…" -ForegroundColor Cyan
    docker run --rm `
        -v "${MountSrc}:/src" `
        -w /src `
        $ImageTag
    if ($LASTEXITCODE -ne 0) { throw "pyinstaller 失败" }

    $ExePath = Join-Path $DistDir 'Quick_Sparam\Quick_Sparam'
    if (Test-Path $ExePath) {
        $Size = [math]::Round((Get-ChildItem $DistDir -Recurse | Measure-Object Length -Sum).Sum / 1MB, 1)
        Write-Host "`n[OK] 产物：$ExePath" -ForegroundColor Green
        Write-Host "[OK] 总大小：$Size MB" -ForegroundColor Green
        Write-Host "[OK] 部署：scp -r dist-linux/Quick_Sparam <user>@<centos7-host>:~/" -ForegroundColor Green
    } else {
        throw "未找到产物 $ExePath，检查 pyinstaller 输出"
    }
}
