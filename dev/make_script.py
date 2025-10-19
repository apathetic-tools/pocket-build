#!/usr/bin/env python3
"""
dev/make_script.py
------------------
Concatenate all modular source files into one self-contained `script.py`.

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

# ------------------------------------------------------------
# Module order (defines both build order and shim targets)
# ------------------------------------------------------------
ORDER_NAMES = [
    "constants",
    "meta",
    "types",
    "utils_core",  # needed before runtime.py
    "runtime",
    "utils_runtime",
    "config",
    "build",
    "actions",
    "cli",
]
ORDER = [f"{n}.py" for n in ORDER_NAMES]
SHIM_NAMES = [n for n in ORDER_NAMES if not n.startswith("_")]

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
        else:  # isinstance(node, ast.Import):
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


def detect_name_collisions(sources: dict[str, str]) -> None:
    """Detect top-level name collisions across modules."""

    # list of harmless globals we don't mind having overwitten
    IGNORE = {
        "__all__",
        "__version__",
        "__author__",
        "__path__",
        "__package__",
        "__commit__",
    }

    symbols: dict[str, str] = {}  # name -> module
    collisions: list[tuple[str, str, str]] = []

    for mod, text in sources.items():
        try:
            tree = ast.parse(text)
        except SyntaxError as e:
            print(f"❌ Failed to parse {mod}: {e}")
            continue

        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
                name = node.name
            elif isinstance(node, ast.Assign):
                # only consider simple names like x = ...
                targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
                if not targets:
                    continue
                name = targets[0]
            else:
                continue

            # skip known harmless globals
            if name in IGNORE:
                continue

            prev = symbols.get(name)
            if prev:
                collisions.append((name, prev, mod))
            else:
                symbols[name] = mod

    if collisions:
        print("❌ Detected potential top-level name collisions:")
        for name, a, b in collisions:
            print(f"   - {name!r} defined in both {a} and {b}")
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

    from datetime import datetime, timezone

    build_date = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    all_imports: "OrderedDict[str, None]" = OrderedDict()
    parts: list[str] = []

    # imports for shim
    all_imports.setdefault("import sys\n", None)

    # for name collision detection
    module_sources: dict[str, str] = {}

    for filename in ORDER:
        path = SRC_DIR / filename
        if not path.exists():
            print(f"⚠️  Skipping missing module: {filename}")
            continue

        text = path.read_text(encoding="utf-8")
        text = strip_redundant_blocks(text)
        module_sources[filename] = text

        imports, body = split_imports(text, package_name)
        for imp in imports:
            all_imports.setdefault(imp, None)

        header = f"# === {filename} ==="
        parts.append(f"\n{header}\n{body.strip()}\n\n")

    # --- Detect potential collisions ---
    detect_name_collisions(module_sources)

    future_imports: "OrderedDict[str, None]" = OrderedDict()
    for imp in list(all_imports.keys()):
        if imp.strip().startswith("from __future__"):
            future_imports.setdefault(imp, None)
            del all_imports[imp]

    future_block = "".join(future_imports.keys())
    import_block = "".join(all_imports.keys())

    shim_block = [
        "# --- import shims for single-file runtime ---",
        "_pkg = 'pocket_build'",
        "_mod = sys.modules.get(f'{_pkg}_single') or sys.modules.get(_pkg)",
        "if _mod:",
        *[f"    sys.modules[f'{{_pkg}}.{name}'] = _mod" for name in SHIM_NAMES],
        "del _pkg, _mod",
        "",
    ]
    shim_text = "\n".join(shim_block)

    final_script = (
        "#!/usr/bin/env python3\n"
        f"{LICENSE_HEADER}\n"
        f"# Version: {version}\n"
        f"# Commit: {commit}\n"
        f"# Build Date: {build_date}\n"
        f"# Repo: https://github.com/apathetic-tools/pocket-build\n"
        "\n# ruff: noqa: E402\n"
        "\n"
        f"{future_block}\n"
        '"""\n'
        "Pocket Build — a tiny build system that fits in your pocket.\n"
        "This single-file version is auto-generated from modular sources.\n"
        f"Version: {version}\n"
        f"Commit: {commit}\n"
        f"Built: {build_date}\n"
        '"""\n\n'
        f"{import_block}\n"
        "\n"
        # constants come *after* imports to avoid breaking __future__ rules
        f"__version__ = {version!r}\n"
        f"__commit__ = {commit!r}\n"
        f"__build_date__ = {build_date!r}\n"
        "\n"
        "\n" + "\n".join(parts) + "\n"
        f"{shim_text}\n"
        "\nif __name__ == '__main__':\n"
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
        help="Custom output path for generated script (default: bin/script.py)",
    )
    args = parser.parse_args()

    out_path = Path(args.out).expanduser().resolve() if args.out else DEFAULT_OUT_FILE
    build_single_file(out_path, package_name=args.package)

    verify_compiles(out_path)

    size = out_path.stat().st_size / 1024
    print(f"📦 Output size: {size:.1f} KB")


if __name__ == "__main__":
    main()
