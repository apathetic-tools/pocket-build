import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from .build import run_build
from .config import parse_builds
from .utils import RESET, YELLOW, load_jsonc


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="pocket-build")
    parser.add_argument("--out", help="Override output directory")
    args = parser.parse_args(argv)

    if sys.version_info < (3, 10):
        sys.exit("❌ pocket-build requires Python 3.10 or newer.")

    cwd = Path.cwd().resolve()
    config_path: Optional[Path] = None

    for candidate in [".pocket-build.json"]:
        p = cwd / candidate
        if p.exists():
            config_path = p
            break

    if not config_path:
        print(f"{YELLOW}⚠️  No build config found (.pocket-build.json).{RESET}")
        return 1

    config_dir = config_path.parent.resolve()
    print(f"🔧 Using config: {config_path.name}")
    print(f"📁 Config base: {config_dir}")
    print(f"📂 Invoked from: {cwd}\n")

    raw_config: Dict[str, Any] = load_jsonc(config_path)
    builds = parse_builds(raw_config)
    print(f"🔧 Running {len(builds)} build(s)\n")

    for i, build_cfg in enumerate(builds, 1):
        print(f"▶️  Build {i}/{len(builds)}")
        run_build(build_cfg, config_dir, args.out)

    print("🎉 All builds complete.")
    return 0
