# -*- mode: python ; coding: utf-8 -*-
# Linux 打包脚本（目标：glibc 2.17，CentOS 7 / RHEL 7）
# 必须在 manylinux2014 容器内构建，详见 packaging/linux/Dockerfile + build_linux.ps1。
# 前置条件：代码已从 PyQt6 迁移到 PyQt5（PyQt6 wheel 依赖 glibc 2.28+，目标系统不支持）。

import os
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

# PyQt5 子模块通常不需要全量收集；只在缺失时按需添加。
hiddenimports = []

a = Analysis(
    ['Quick_Sparam_B.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('resources', 'resources'),
        # samples/ 不打入，发布体积控制；如需调试可临时加上
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['pyinstaller_hooks/set_limited_env.py'],
    excludes=[
        # 显式排除 PyQt6，防止环境里残留时被误打包
        'PyQt6',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        # Windows-only 依赖
        'pywin32',
        'pywin32_ctypes',
        'pefile',
        'winrm',
        'pyspnego',
        'sspilib',
        'requests_ntlm',
        # 开发期 GUI 助手
        'auto_py_to_exe',
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Quick_Sparam',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,                 # Linux 下 upx 与 Qt 插件兼容性差，先关掉
    console=False,             # GUI 程序；首次部署排错可临时改 True
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # Linux 下 PyInstaller 不使用 icon 字段，故省略
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='Quick_Sparam',
)
