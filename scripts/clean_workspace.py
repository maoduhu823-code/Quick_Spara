"""清理本机工作区里的临时产物 / 缓存。

用法：
    python scripts/clean_workspace.py            # 实际执行
    python scripts/clean_workspace.py --dry-run  # 只列要删的内容，不动手

PyCharm 用法：直接右键 → Run。

删除范围：
- PyInstaller 产物：dist/、build/、dist-linux/、build-linux/
- Python 缓存：所有 __pycache__/（递归）、.pytest_cache/、.mypy_cache/、.ruff_cache/
- AI 工具本地缓存：.codexbridge/、.claude/settings.local.json
- 运行时反馈数据：Public/data_feedback/inbox/（含隐私 JSON）
- 性能日志：importtime_*.txt
"""
import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# 顶层固定目标
TOP_DIRS = [
    "dist", "build", "dist-linux", "build-linux",
    ".pytest_cache", ".mypy_cache", ".ruff_cache",
    ".codexbridge",
    "Public/data_feedback/inbox",
]
TOP_FILES = [".claude/settings.local.json"]


def dir_size(p: Path) -> int:
    return sum(f.stat().st_size for f in p.rglob("*") if f.is_file())


def remove(path: Path, dry_run: bool) -> int:
    if not path.exists():
        return 0
    size = path.stat().st_size if path.is_file() else dir_size(path)
    mb = size / 1024 / 1024
    rel = path.relative_to(ROOT)
    if dry_run:
        print(f"  [dry-run] would remove {rel}  ({mb:.2f} MB)")
    else:
        print(f"  remove {rel}  ({mb:.2f} MB)")
        if path.is_file():
            path.unlink()
        else:
            shutil.rmtree(path)
    return size


def main():
    parser = argparse.ArgumentParser(description="清理本机工作区临时产物")
    parser.add_argument("--dry-run", action="store_true", help="只列要删的，不实际删除")
    args = parser.parse_args()

    total = 0

    # 1. 顶层固定目录
    for rel in TOP_DIRS:
        total += remove(ROOT / rel, args.dry_run)

    # 2. 顶层固定文件
    for rel in TOP_FILES:
        total += remove(ROOT / rel, args.dry_run)

    # 3. 递归 __pycache__（跳过 .git / .venv）
    skip = {".git", ".venv"}
    for cache in ROOT.rglob("__pycache__"):
        if any(part in skip for part in cache.parts):
            continue
        total += remove(cache, args.dry_run)

    # 4. importtime_*.txt
    for log in ROOT.glob("importtime_*.txt"):
        total += remove(log, args.dry_run)

    prefix = "预计可回收" if args.dry_run else "已回收"
    print(f"\n{prefix}: {total / 1024 / 1024:.1f} MB")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
