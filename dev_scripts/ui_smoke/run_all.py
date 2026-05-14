from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dev_scripts.ui_smoke.harness import SmokeContext, configure_environment


MODULES = {
    "main": "dev_scripts.ui_smoke.cases_main",
    "diff": "dev_scripts.ui_smoke.cases_diff",
    "port": "dev_scripts.ui_smoke.cases_port",
    "cascade": "dev_scripts.ui_smoke.cases_cascade",
    "ripple": "dev_scripts.ui_smoke.cases_ripple",
    "freq_analysis": "dev_scripts.ui_smoke.cases_freq_analysis",
    "time_domain": "dev_scripts.ui_smoke.cases_time_domain",
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Visible UI smoke tests for Quick_Sparam."
    )
    parser.add_argument(
        "--module",
        choices=["all", *MODULES.keys()],
        default="all",
        help="Run one module or the full smoke suite.",
    )
    parser.add_argument(
        "--input-dir",
        default=None,
        help="Directory containing Touchstone files. Defaults to ./input if present, otherwise ./samples.",
    )
    parser.add_argument(
        "--limit-samples",
        type=int,
        default=3,
        help="Number of S-parameter files to load into the visible UI.",
    )
    parser.add_argument(
        "--pause-ms",
        type=int,
        default=40,
        help="Small UI event delay after each action.",
    )
    parser.add_argument(
        "--keep-open-ms",
        type=int,
        default=0,
        help="Keep the final visible UI open for this many milliseconds.",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run a shorter subset of heavy plot/action combinations.",
    )
    parser.add_argument(
        "--list-modules",
        action="store_true",
        help="Print module names and exit.",
    )
    return parser.parse_args(argv)


def load_case(module_path: str):
    module_name = module_path.rsplit(".", 1)[-1]
    module = __import__(module_path, fromlist=[module_name])
    return module


def main(argv: list[str] | None = None) -> int:
    configure_environment()
    args = parse_args(argv)
    if args.list_modules:
        print("\n".join(MODULES))
        return 0

    selected = list(MODULES.items()) if args.module == "all" else [(args.module, MODULES[args.module])]

    with SmokeContext(args, REPO_ROOT) as ctx:
        for name, module_path in selected:
            module = load_case(module_path)
            module.run(ctx)
        ctx.keep_open_if_requested()
        ctx.report.print_summary()
        return 1 if ctx.report.fail_count else 0


if __name__ == "__main__":
    raise SystemExit(main())
