#!/usr/bin/env python3
"""
dev/make_script.py
------------------
Concatenate all modular source files into one self-contained `pocket-build.py`.

Produces a portable single-file build system ready for direct use or release.
All internal and relative imports are stripped, and all remaining imports are
collected, deduplicated, and placed neatly at the top.
"""

import argparse
import os
import re
import subprocess
from pathlib import Path

# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT / "src" / "pocket_build"
DEFAULT_OUT_FILE = ROOT / "bin" / "pocket-build.py"
PYPROJECT = ROOT / "pyproject.toml"

ORDER = [
    "types.py",
    "utils.py",
    "config.py",
    "build.py",
    "cli.py",
]

LICENSE_HEADER = """\
# Pocket Build — a tiny build system that fits in your pocket.
# License: MIT-NOAI
# Full text: https://github.com/apathetic-tools/pocket-build/blob/main/LICENSE
"""


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------
def extract_version() -> str:
    if not PYPROJECT.exists():
        return "unknown"
    text = PYPROJECT.read_text(encoding="utf-8")
    match = re.search(r'(?m)^\s*version\s*=\s*["\']([^"\']+)["\']', text)
    return match.group(1) if match else "unknown"


def extract_commit() -> str:
    # Only embed commit hash if in CI or release tag context
    if not (os.getenv("CI") or os.getenv("GIT_TAG") or os.getenv("GITHUB_REF")):
        return "unknown (local build)"
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()

    except subprocess.CalledProcessError as e:
        print(f"[warn] git rev-parse failed: {e.stderr.strip()}")
    except FileNotFoundError:
        print("[warn] git not available in environment")

    return "unknown"


def split_imports(text: str) -> tuple[list[str], str]:
    """Split module text into (imports, rest), normalizing indentation."""
    imports: list[str] = []
    body_lines: list[str] = []
    for line in text.splitlines():
        stripped = line.lstrip()
        if re.match(r"^(?:import|from)\s+\S+", stripped):
            imports.append(stripped)
        else:
            body_lines.append(line)
    return imports, "\n".join(body_lines)


def strip_internal_imports(lines: list[str]) -> list[str]:
    """Remove intra-package (`pocket_build.*`) and relative (`.foo`) imports."""
    filtered: list[str] = []
    for line in lines:
        if re.match(r"^\s*(?:from|import)\s+pocket_build(\.|$)", line):
            continue
        if re.match(r"^\s*from\s+\.", line):
            continue
        filtered.append(line)
    return filtered


def strip_redundant_blocks(text: str) -> str:
    """Remove shebangs and __main__ guards."""
    text = re.sub(r"^#!.*\n", "", text)
    text = re.sub(r'if\s+__name__\s*==\s*[\'"]__main__[\'"]\s*:\n\s*.*', "", text)
    return text.strip()


# ------------------------------------------------------------
# Build process
# ------------------------------------------------------------
def build_single_file(out_path: Path) -> None:
    version = extract_version()
    commit = extract_commit()

    all_imports: set[str] = set()
    parts: list[str] = []

    for filename in ORDER:
        path = SRC_DIR / filename
        if not path.exists():
            print(f"⚠️  Skipping missing module: {filename}")
            continue

        text = path.read_text(encoding="utf-8")
        text = strip_redundant_blocks(text)

        imports, body = split_imports(text)
        imports = strip_internal_imports(imports)
        all_imports.update(imports)

        header = f"# === {filename} ==="
        parts.append(f"\n{header}\n{body.strip()}\n")

    sorted_imports = "\n".join(sorted(all_imports))

    final_script = (
        "#!/usr/bin/env python3\n"
        f"{LICENSE_HEADER}\n"
        f"# Version: {version}\n"
        f"# Commit: {commit}\n"
        f"# Repo: https://github.com/apathetic-tools/pocket-build\n"
        "\n"
        '"""\n'
        "Pocket Build — a tiny build system that fits in your pocket.\n"
        "This single-file version is auto-generated from modular sources.\n"
        f"Version: {version}\n"
        f"Commit: {commit}\n"
        '"""\n\n'
        f"{sorted_imports}\n"
        "\n" + "\n".join(parts) + "\n\nif __name__ == '__main__':\n"
        "    import sys\n"
        "    sys.exit(main(sys.argv[1:]))\n"
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(final_script, encoding="utf-8")
    out_path.touch()

    rel_path = out_path.relative_to(ROOT) if out_path.is_relative_to(ROOT) else out_path
    print(f"✅ Built {rel_path} ({len(parts)} modules) — version {version} ({commit}).")

    # 🧹 Auto-format if possible
    try:
        result = subprocess.run(
            ["poetry", "run", "poe", "fix"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print("✨ Auto-formatted using 'poe fix'.")
        else:
            print(f"⚠️  'poe fix' failed:\n{result.stderr.strip()}")
    except FileNotFoundError:
        print("⚠️  Poetry or Poe not found — skipping auto-formatting.")


# ------------------------------------------------------------
# CLI entry point
# ------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Bundle Pocket Build into a single script."
    )
    parser.add_argument(
        "--out",
        type=str,
        help="Custom output path for generated script (default: bin/pocket-build.py)",
    )
    args = parser.parse_args()

    out_path = Path(args.out).expanduser().resolve() if args.out else DEFAULT_OUT_FILE
    build_single_file(out_path)


if __name__ == "__main__":
    main()
