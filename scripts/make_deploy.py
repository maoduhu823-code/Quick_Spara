"""生成 Linux 友好的部署包 Quick_Sparam_deploy_<日期>.<格式>。

用法：
    python scripts/make_deploy.py                    # 默认 tar.gz，输出到工程根
    python scripts/make_deploy.py --format zip       # 改 zip 格式
    python scripts/make_deploy.py --output D:\\out   # 指定输出目录

PyCharm 用法：直接右键 → Run。

设计：白名单制 —— 只把"打包/安装必需 + 用户使用指南"打进去；目录内会按
EXCLUDE_PATTERNS 过滤（__pycache__、.venv、build/dist 等不会带进去）。

公司 Linux 端解开后流程：
    tar -xzf Quick_Sparam_deploy_*.tar.gz
    cd Quick_Sparam
    python3.11 -m venv .venv && source .venv/bin/activate
    pip install -r packaging/linux/requirements-linux.txt
    pyinstaller --noconfirm Quick_Sparam_linux.spec
"""
import argparse
import datetime
import shutil
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# 白名单：要带进包的顶层路径（相对工程根）
INCLUDE = [
    # 入口与核心模块
    "Quick_Sparam_B.py",
    "Quick_Sparam_install.pyw",
    "app_utils.py",
    "main_window.py",
    "sparam_core.py",
    # 业务包
    "QS_domain",
    "QS_services",
    "QS_infra",
    "QS_dialogs",
    "QS_runtime_services",
    # 资源 + 打包脚手架
    "resources",
    "pyinstaller_hooks",
    "packaging",
    "scripts",
    # 打包配置
    "requirements.txt",
    "Quick_Sparam_install.spec",
    "Quick_Sparam_linux.spec",
    "build_linux.ps1",
    # 单元测试（Linux 端先 pytest 验证用）
    "tests",
    # 元信息 + 文档精选
    "CLAUDE.md",
    "AGENTS.md",
    ".gitignore",
    "docs/AGENT_GUIDE.md",
    "docs/ARCHITECTURE.md",
    "docs/CONVENTIONS.md",
    "docs/INTERFACES.md",
    "docs/Quick_Sparam_使用指南.html",
    "docs/Quick_Sparam_功能介绍与使用指南.pptx",
]

# 目录内过滤：shutil.ignore_patterns 风格的通配
EXCLUDE_PATTERNS = (
    "__pycache__", "*.pyc", "*.pyo", "*.pyd",
    ".pytest_cache", ".mypy_cache", ".ruff_cache",
    ".idea", ".codexbridge", ".venv",
    "build", "dist", "build-linux", "dist-linux",
    "importtime_*.txt",
)


def stage(staging_root: Path) -> tuple[int, int]:
    """把白名单内容拷到 staging_root 下，返回 (拷贝项数, 缺失项数)。"""
    ok = miss = 0
    ignore = shutil.ignore_patterns(*EXCLUDE_PATTERNS)
    for rel in INCLUDE:
        src = ROOT / rel
        if not src.exists():
            print(f"  ! 缺失（跳过）：{rel}")
            miss += 1
            continue
        dst = staging_root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, dst, ignore=ignore, dirs_exist_ok=True)
        else:
            shutil.copy2(src, dst)
        ok += 1
    return ok, miss


def make_tar_gz(staging: Path, archive: Path) -> None:
    with tarfile.open(archive, "w:gz") as tar:
        tar.add(staging / "Quick_Sparam", arcname="Quick_Sparam")


def make_zip(staging: Path, archive: Path) -> None:
    base = staging / "Quick_Sparam"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in base.rglob("*"):
            if p.is_file():
                z.write(p, arcname=p.relative_to(staging))


def main():
    parser = argparse.ArgumentParser(description="生成 Quick_Sparam 部署包")
    parser.add_argument("--format", choices=["tar.gz", "zip"], default="tar.gz",
                        help="包格式（默认 tar.gz，Linux 友好）")
    parser.add_argument("--output", type=Path, default=ROOT,
                        help="输出目录（默认工程根）")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    date = datetime.date.today().strftime("%Y%m%d")
    archive = args.output / f"Quick_Sparam_deploy_{date}.{args.format}"
    if archive.exists():
        archive.unlink()

    with tempfile.TemporaryDirectory(prefix="qs_deploy_") as tmpdir:
        staging = Path(tmpdir)
        staging_root = staging / "Quick_Sparam"
        staging_root.mkdir()

        print(f"[1/2] 收集白名单到 {staging_root}")
        ok, miss = stage(staging_root)
        print(f"      已拷贝 {ok} 项，缺失 {miss} 项")

        print(f"[2/2] 打包 → {archive}")
        if args.format == "zip":
            make_zip(staging, archive)
        else:
            make_tar_gz(staging, archive)

    size_mb = archive.stat().st_size / 1024 / 1024
    print(f"\n[OK] 产物：{archive}  ({size_mb:.2f} MB)")
    print("[OK] 公司 Linux 端解开后：")
    print(f"       tar -xzf {archive.name}" if args.format == "tar.gz"
          else f"       unzip {archive.name}")
    print("       cd Quick_Sparam")
    print("       python3.11 -m venv .venv && source .venv/bin/activate")
    print("       pip install -r packaging/linux/requirements-linux.txt")
    print("       pyinstaller --noconfirm Quick_Sparam_linux.spec")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
