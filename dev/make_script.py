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
import ast
import os
import re
import subprocess
from collections import OrderedDict
from pathlib import Path

# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT / "src" / "pocket_build"
DEFAULT_OUT_FILE = ROOT / "bin" / "pocket-build.py"
PYPROJECT = ROOT / "pyproject.toml"

ORDER = [
    "meta.py",
    "runtime.py",
    "types.py",
    "utils.py",
    "config.py",
    "build.py",
    "cli.py",
]
# ORDER = [p.name for p in SRC_DIR.glob("*.py") if p.name != "__init__.py"]

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


def split_imports(
    text: str,
    package_name: str,
) -> tuple[list[str], str]:
    """Return (external_imports, body_text) using AST for accuracy."""
    try:
        tree = ast.parse(text)
    except SyntaxError as e:
        print(f"❌ Failed to parse file: {e}")
        return [], text

    lines = text.splitlines(keepends=True)
    external_imports: list[str] = []
    all_import_ranges: list[tuple[int, int]] = []

    for node in tree.body:
        if not isinstance(node, (ast.Import, ast.ImportFrom)):
            continue

        start = node.lineno - 1
        end = getattr(node, "end_lineno", node.lineno)
        snippet = "".join(lines[start:end])

        # --- Determine whether it's internal ---
        is_internal = False
        if isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if node.level > 0 or mod.startswith(package_name):
                is_internal = True
        elif isinstance(node, ast.Import):
            if any(alias.name.startswith(package_name) for alias in node.names):
                is_internal = True

        # Always skip import lines from body, internal or not
        all_import_ranges.append((start, end))

        # Only keep non-internal imports for the top section
        if not is_internal:
            external_imports.append(snippet)

    # --- Remove *all* import lines from the body ---
    skip = {i for s, e in all_import_ranges for i in range(s, e)}
    body = "".join(line for i, line in enumerate(lines) if i not in skip)

    return external_imports, body


def strip_redundant_blocks(text: str) -> str:
    """Remove shebangs and __main__ guards."""
    text = re.sub(r"^#!.*\n", "", text)
    text = re.sub(
        r"(?s)\n?if\s+__name__\s*==\s*[\"']__main__[\"']\s*:\s*\n.*?$", "", text
    )

    return text.strip()


def verify_compiles(path: Path) -> None:
    """Ensure the generated script compiles cleanly."""
    import py_compile

    try:
        py_compile.compile(str(path), doraise=True)
        print("✅ Compiled successfully.")
    except py_compile.PyCompileError as e:
        print(f"❌ Syntax error in generated script: {e.msg}")
        raise SystemExit(1)


# ------------------------------------------------------------
# Build process
# ------------------------------------------------------------
def build_single_file(
    out_path: Path,
    package_name: str,
) -> None:
    version = extract_version()
    commit = extract_commit()

    all_imports: "OrderedDict[str, None]" = OrderedDict()
    parts: list[str] = []

    for filename in ORDER:
        path = SRC_DIR / filename
        if not path.exists():
            print(f"⚠️  Skipping missing module: {filename}")
            continue

        text = path.read_text(encoding="utf-8")
        text = strip_redundant_blocks(text)

        imports, body = split_imports(text, package_name)
        for imp in imports:
            all_imports.setdefault(imp, None)

        header = f"# === {filename} ==="
        parts.append(f"\n{header}\n{body.strip()}\n\n")

    import_block = "".join(all_imports.keys())

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
        f"{import_block}\n"
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
            check=False,
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
        "--package",
        default="pocket_build",
        help="Root package name (default: pocket_build)",
    )
    parser.add_argument(
        "--out",
        type=str,
        help="Custom output path for generated script (default: bin/pocket-build.py)",
    )
    args = parser.parse_args()

    out_path = Path(args.out).expanduser().resolve() if args.out else DEFAULT_OUT_FILE
    build_single_file(out_path, package_name=args.package)

    verify_compiles(out_path)

    size = out_path.stat().st_size / 1024
    print(f"📦 Output size: {size:.1f} KB")


if __name__ == "__main__":
    main()
