from __future__ import annotations

import argparse
import fnmatch
import os
import subprocess
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
VCS_DIRS = {".git", ".hg", ".svn"}
FORCE_INCLUDE_PATHS = (
    "Quick_Sparam_B.py",
    "Quick_Sparam_install.pyw",
    "Quick_Sparam_install.spec",
    "requirements.txt",
)
FORCE_INCLUDE_DIRS = ("resources", "pyinstaller_hooks")


@dataclass(frozen=True)
class GeneratedFile:
    arcname: str
    content: str


@dataclass(frozen=True)
class IgnoreRule:
    pattern: str
    directory_only: bool
    negated: bool

    def matches(self, rel_path: str) -> bool:
        rel_path = rel_path.strip("/")
        pattern = self.pattern.strip("/")
        if not pattern:
            return False

        parts = rel_path.split("/")
        has_slash = "/" in pattern

        if self.directory_only:
            if has_slash:
                return rel_path == pattern or rel_path.startswith(f"{pattern}/")
            return any(fnmatch.fnmatchcase(part, pattern) for part in parts)

        if has_slash:
            return fnmatch.fnmatchcase(rel_path, pattern)
        return fnmatch.fnmatchcase(parts[-1], pattern)


def load_gitignore_rules(root: Path) -> list[IgnoreRule]:
    gitignore = root / ".gitignore"
    if not gitignore.exists():
        return []

    rules: list[IgnoreRule] = []
    for raw_line in gitignore.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        negated = line.startswith("!")
        if negated:
            line = line[1:]

        directory_only = line.endswith("/")
        rules.append(
            IgnoreRule(
                pattern=line,
                directory_only=directory_only,
                negated=negated,
            )
        )
    return rules


def rel_posix(path: Path) -> str:
    return path.relative_to(PROJECT_ROOT).as_posix()


def is_ignored(rel_path: str, rules: list[IgnoreRule]) -> bool:
    ignored = False
    for rule in rules:
        if rule.matches(rel_path):
            ignored = not rule.negated
    return ignored


def should_package(path: Path, rules: list[IgnoreRule]) -> bool:
    rel_path = rel_posix(path)
    return not is_ignored(rel_path, rules)


def split_nul(text: str) -> list[str]:
    return [item for item in text.split("\0") if item]


def run_git(root: Path, args: list[str], stdin: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        input=stdin,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="surrogateescape",
        check=False,
    )


def path_from_git(root: Path, rel_path: str) -> Path | None:
    root_resolved = root.resolve()
    path = (root / rel_path).resolve()
    if not path.is_relative_to(root_resolved) or not path.is_file():
        return None
    return path


def collect_files_with_git(root: Path) -> list[Path] | None:
    files_proc = run_git(
        root,
        ["ls-files", "-z", "--cached", "--others", "--exclude-standard"],
    )
    if files_proc.returncode != 0:
        return None

    rel_paths = split_nul(files_proc.stdout)
    if not rel_paths:
        return []

    # git ls-files includes tracked files even if they now match .gitignore.
    # check-ignore --no-index lets the ignore file remain the final authority.
    check_proc = run_git(
        root,
        ["check-ignore", "--no-index", "-z", "--stdin"],
        "\0".join(rel_paths) + "\0",
    )
    if check_proc.returncode not in (0, 1):
        return None

    ignored_paths = set(split_nul(check_proc.stdout))
    files: list[Path] = []
    for rel_path in rel_paths:
        if rel_path in ignored_paths:
            continue
        path = path_from_git(root, rel_path)
        if path is not None:
            files.append(path)

    return sorted(set(files), key=rel_posix)


def collect_files_with_gitignore_fallback(root: Path) -> list[Path]:
    rules = load_gitignore_rules(root)
    files: list[Path] = []
    root_resolved = root.resolve()

    for dirpath, dirnames, filenames in os.walk(root):
        current_dir = Path(dirpath)
        rel_dir = (
            current_dir.relative_to(root_resolved).as_posix()
            if current_dir != root_resolved
            else ""
        )

        kept_dirs: list[str] = []
        for dirname in dirnames:
            if dirname in VCS_DIRS:
                continue
            rel_path = f"{rel_dir}/{dirname}".strip("/")
            if is_ignored(rel_path, rules) or is_ignored(f"{rel_path}/", rules):
                continue
            kept_dirs.append(dirname)
        dirnames[:] = kept_dirs

        for filename in filenames:
            path = current_dir / filename
            if should_package(path, rules):
                files.append(path)

    return sorted(files, key=rel_posix)


def collect_forced_files(root: Path) -> list[Path]:
    """Return migration-critical files even when .gitignore excludes them."""
    root_resolved = root.resolve()
    files: set[Path] = set()

    for rel_path in FORCE_INCLUDE_PATHS:
        path = (root / rel_path).resolve()
        if path.is_relative_to(root_resolved) and path.is_file():
            files.add(path)

    for rel_dir in FORCE_INCLUDE_DIRS:
        directory = (root / rel_dir).resolve()
        if not directory.is_relative_to(root_resolved) or not directory.is_dir():
            continue
        for path in directory.rglob("*"):
            if path.is_file():
                files.add(path.resolve())

    return sorted(files, key=rel_posix)


def collect_package_files(root: Path) -> tuple[list[Path], str, list[Path]]:
    files = collect_files_with_git(root)
    if files is not None:
        collection_source = "git"
    else:
        files = collect_files_with_gitignore_fallback(root)
        collection_source = "filesystem"

    file_set = set(files)
    forced_files = [path for path in collect_forced_files(root) if path not in file_set]
    file_set.update(forced_files)
    return sorted(file_set, key=rel_posix), collection_source, forced_files


def generated_package_files() -> list[GeneratedFile]:
    readme = """Quick_Sparam 迁移包使用说明

1. 复制与解压
   - 把本 zip 复制到另一台电脑后，先完整解压，不要直接在压缩包里运行。
   - 用 PyCharm 打开解压后的 Quick_Sparam 文件夹。

2. 在 PyCharm 里运行源码
   - 建议新建虚拟环境，或选择已经安装依赖的解释器。
   - 在 PyCharm Terminal 执行：python -m pip install -r requirements.txt
   - 正常运行入口：Quick_Sparam_B.py
   - 本地调试入口：Quick_Sparam_B.py --dev（在 Run Config 里加 --dev 参数）

3. 使用 PyInstaller 生成 exe
   - 在解压后的项目根目录执行：python -m PyInstaller Quick_Sparam_install.spec
   - 也可以双击 build_with_pyinstaller.bat 自动安装依赖并打包。
   - 生成结果位于：dist/Quick_Sparam_install/Quick_Sparam_install.exe

4. 打包说明
   - Quick_Sparam_install.spec 会被强制放入本迁移包，即使项目 .gitignore 排除了 *.spec。
   - resources/ 会被强制放入本迁移包，保证图标和界面图片能被 PyInstaller 收集。
"""
    build_bat = """@echo off
setlocal
cd /d "%~dp0"

echo Installing dependencies from requirements.txt...
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo Dependency installation failed.
    pause
    exit /b %errorlevel%
)

echo Building Quick_Sparam with PyInstaller...
python -m PyInstaller Quick_Sparam_install.spec
if errorlevel 1 (
    echo PyInstaller build failed.
    pause
    exit /b %errorlevel%
)

echo Done. EXE: dist\\Quick_Sparam_install\\Quick_Sparam_install.exe
pause
"""
    return [
        GeneratedFile("INSTALL_README.txt", readme),
        GeneratedFile("build_with_pyinstaller.bat", build_bat),
    ]


def default_archive_path(root: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return root.parent / f"{root.name}_install_{stamp}.zip"


def format_size(num_bytes: int) -> str:
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} {unit}"
        size /= 1024
    return f"{num_bytes} B"


def print_scope(
    files: list[Path],
    output_path: Path,
    collection_source: str,
    forced_files: list[Path],
    generated_files: list[GeneratedFile],
) -> None:
    total_size = sum(path.stat().st_size for path in files)
    print("安装包打包范围（执行前确认）")
    print(f"项目根目录: {PROJECT_ROOT}")
    print(f"输出文件: {output_path}")
    if collection_source == "git":
        print("选择方式: Git 已跟踪文件 + 未被 .gitignore 排除的未跟踪文件")
    else:
        print("选择方式: 文件系统遍历 + 根目录 .gitignore 排除规则")
    print(f"文件数量: {len(files)}")
    print(f"总大小: {format_size(total_size)}")
    print()

    print("排除规则:")
    print("  - .gitignore / Git 标准排除规则")
    print("  - .git、.hg、.svn 等版本库内部目录")
    print()
    print("强制包含:")
    print("  - Quick_Sparam_install.spec（PyInstaller 打包配置）")
    print("  - Quick_Sparam_B.py（统一入口）/ Quick_Sparam_install.pyw（精简版启动器）")
    print("  - pyinstaller_hooks/（PyInstaller runtime hook）")
    print("  - requirements.txt")
    print("  - resources/（图标和界面图片）")

    if forced_files:
        print()
        print("本次因迁移/打包需求额外纳入的文件:")
        for path in forced_files:
            print(f"  - {rel_posix(path)}")

    if generated_files:
        print()
        print("压缩包内自动生成的辅助文件:")
        for generated_file in generated_files:
            print(f"  - {generated_file.arcname}")

    print()
    print("最终文件清单:")
    for path in files:
        print(f"  - {rel_posix(path)}")


def ask_for_confirmation() -> bool:
    try:
        answer = input("\n确认创建压缩包？输入 y/yes/是 继续: ").strip().lower()
    except EOFError:
        return False
    return answer in {"y", "yes", "是"}


def create_archive(files: list[Path], output_path: Path, generated_files: list[GeneratedFile]) -> None:
    written_arcnames: set[str] = set()
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for path in files:
            arcname = rel_posix(path)
            zipf.write(path, arcname)
            written_arcnames.add(arcname)
            print(f"已添加: {arcname}")

        for generated_file in generated_files:
            if generated_file.arcname in written_arcnames:
                print(f"跳过生成辅助文件，压缩包内已存在同名文件: {generated_file.arcname}")
                continue
            zipf.writestr(generated_file.arcname, generated_file.content)
            print(f"已生成: {generated_file.arcname}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="按 .gitignore 自动创建可迁移源码包，并保留 PyInstaller 打包所需文件。"
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="输出 zip 路径；默认写到项目同级目录并带时间戳。",
    )
    parser.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="跳过确认，直接创建压缩包。",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只显示打包范围，不创建压缩包。",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    generated_files = generated_package_files()
    output_path = args.output or default_archive_path(PROJECT_ROOT)
    if not output_path.is_absolute():
        output_path = PROJECT_ROOT / output_path

    files, collection_source, forced_files = collect_package_files(PROJECT_ROOT)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    files = [path for path in files if path.resolve() != output_path.resolve()]

    print_scope(files, output_path, collection_source, forced_files, generated_files)

    if args.dry_run:
        print("\n--dry-run：仅显示范围，未创建压缩包。")
        return 0

    if not args.yes and not ask_for_confirmation():
        print("未确认，已取消；没有创建压缩包。")
        return 0

    create_archive(files, output_path, generated_files)
    print(f"\n成功创建安装包: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
