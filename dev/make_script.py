#!/usr/bin/env python3
"""dev/make_script.py
------------------
Concatenate all modular source files into one self-contained `script.py`.

Produces a portable single-file build system ready for direct use or release.
All internal and relative imports are stripped, and all remaining imports are
collected, deduplicated, and placed neatly at the top.
"""

import argparse
import ast
import graphlib
import importlib
import os
import py_compile
import re
import subprocess
from collections import OrderedDict
from datetime import datetime, timezone
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
ORDER_NAMES: list[str] = [
    "constants",
    "meta",
    "config_types",  # needed before utils.py
    "utils_logs",  # needed before logs.py
    "logs",
    "utils",
    "utils_types",
    "utils_schema",
    "config",
    "config_resolve",
    "config_validate",
    "build",
    "actions",
    "cli",
]
ORDER = [f"{n}.py" for n in ORDER_NAMES]
SHIM_NAMES = [n for n in ORDER_NAMES if not n.startswith("_")]
EXCLUDE_NAMES: list[str] = []

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
            ["git", "rev-parse", "--short", "HEAD"],  # noqa: S607
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
        elif any(alias.name.startswith(package_name) for alias in node.names):
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
        r"(?s)\n?if\s+__name__\s*==\s*[\"']__main__[\"']\s*:\s*\n.*?$",
        "",
        text,
    )

    return text.strip()


def verify_compiles(path: Path) -> None:
    """Ensure the generated script compiles cleanly."""
    try:
        py_compile.compile(str(path), doraise=True)
        print("✅ Compiled successfully.")
    except py_compile.PyCompileError as e:
        print(f"❌ Syntax error in generated script: {e.msg}")
        raise SystemExit(1) from e


def detect_name_collisions(sources: dict[str, str]) -> None:
    """Detect top-level name collisions across modules."""
    # list of harmless globals we don't mind having overwitten
    ignore = {
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
            if name in ignore:
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


def verify_all_modules_listed() -> None:
    """Ensure all .py files in SRC_DIR are listed in ORDER or EXCLUDE_NAMES."""
    all_files = sorted(
        p.name for p in SRC_DIR.glob("*.py") if not p.name.startswith("__")
    )

    known = set(ORDER + [f"{n}.py" for n in EXCLUDE_NAMES])
    unknown = [f for f in all_files if f not in known]

    if unknown:
        print("❌ Unlisted source files detected:")
        for f in unknown:
            print(f"   - {f}")
        print("\nPlease add them to ORDER_NAMES or EXCLUDE_NAMES.")
        raise SystemExit(1)


def detect_internal_import_order(package_name: str) -> None:
    """Warn (or fail) if ORDER_NAMES violates internal import dependencies."""
    deps: dict[str, set[str]] = {name: set() for name in ORDER_NAMES}

    for name in ORDER_NAMES:
        path = SRC_DIR / f"{name}.py"
        if not path.exists():
            continue

        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError as e:
            print(f"❌ Failed to parse {name}.py: {e}")
            continue

        for node in tree.body:
            if isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                if mod.startswith(package_name):
                    dep = mod.split(".")[-1]
                    if dep in deps and dep != name:
                        deps[name].add(dep)

    # detect circular imports first
    try:
        sorter = graphlib.TopologicalSorter(deps)
        topo = list(sorter.static_order())
    except graphlib.CycleError as e:
        print(f"❌ Circular dependency detected: {e.args[1]}")
        raise SystemExit(1) from e

    # compare ORDER_NAMES to topological sort
    mismatched = [
        n for n in ORDER_NAMES if n in topo and topo.index(n) != ORDER_NAMES.index(n)
    ]
    if mismatched:
        print("⚠️  Possible module misordering detected:")
        for n in mismatched:
            print(f"   - {n} appears before one of its dependencies")
        print("💡 Suggested order:")
        print("   " + ", ".join(topo))
        print()


def verify_no_broken_imports(final_text: str, package_name: str) -> None:
    pattern = re.compile(rf"\bimport {package_name}\.(\w+)")
    broken = {
        m.group(1)
        for m in pattern.finditer(final_text)
        if f"# === {m.group(1)}.py ===" not in final_text
    }
    if broken:
        print("❌ Unresolved internal imports remain:")
        for mod in broken:
            print(f"   - {package_name}.{mod}")
        raise SystemExit(1)


def suggest_fixed_order(package_name: str) -> None:
    """Print a suggested ORDER_NAMES sequence based on actual internal imports."""
    deps: dict[str, set[str]] = {name: set() for name in ORDER_NAMES}

    for name in ORDER_NAMES:
        path = SRC_DIR / f"{name}.py"
        if not path.exists():
            continue

        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue

        for node in tree.body:
            if isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                if mod.startswith(package_name):
                    dep = mod.split(".")[-1]
                    if dep in deps and dep != name:
                        deps[name].add(dep)

    sorter = graphlib.TopologicalSorter(deps)
    topo = list(sorter.static_order())

    if topo != ORDER_NAMES:
        print("💡 Suggested ORDER_NAMES based on internal imports:")
        print("   " + ", ".join(topo))


def force_mtime_advance(path: Path, seconds: float = 1.0, max_tries: int = 50) -> None:
    """Reliably bump a file's mtime, preserving atime and nanosecond precision.

    Technicaly should be faster than just sleep and check.

    Ensures the change is visible before returning, even on lazy filesystems.

    We often can't use os.sleep or time.sleep because we monkeypatch it.
    """
    real_time = importlib.import_module("time")  # immune to monkeypatch
    old_m = path.stat().st_mtime_ns
    ns_bump = int(seconds * 1_000_000_000)
    new_m: int = old_m

    for _attempt in range(max_tries):
        st = path.stat()
        os.utime(path, ns=(int(st.st_atime_ns), int(st.st_mtime_ns + ns_bump)))
        os.sync()  # flush kernel metadata

        new_m = path.stat().st_mtime_ns
        if new_m > old_m:
            return  # ✅ success
        real_time.sleep(0.00001)  # 10 µs pause before recheck

    xmsg = (
        f"bump_mtime({path}) failed to advance mtime after {max_tries} attempts "
        f"(old={old_m}, new={new_m})",
    )
    raise AssertionError(xmsg)


# ------------------------------------------------------------
# Build process
# ------------------------------------------------------------
def build_single_file(
    out_path: Path,
    package_name: str,
) -> None:
    version = extract_version()
    commit = extract_commit()

    # check if we missed any files in the module in our ORDER
    verify_all_modules_listed()

    detect_internal_import_order(package_name)
    suggest_fixed_order(package_name)

    build_date = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    all_imports: OrderedDict[str, None] = OrderedDict()

    # imports for shim
    all_imports.setdefault("import sys\n", None)

    parts: list[str] = []

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

    future_imports: OrderedDict[str, None] = OrderedDict()
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
        f"__STANDALONE__ = True\n"
        f"__STITCH_SOURCE__ = 'dev/make_script.py'\n"
        "\n"
        "\n" + "\n".join(parts) + "\n"
        f"{shim_text}\n"
        "\nif __name__ == '__main__':\n"
        "    import sys\n"
        "    sys.exit(main(sys.argv[1:]))\n"
    )

    verify_no_broken_imports(final_script, package_name)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(final_script, encoding="utf-8")

    # Ensure mtime visibly increases across all filesystems
    try:
        force_mtime_advance(out_path)
    except AssertionError as e:
        print(f"⚠️  Could not force mtime advance: {e}")

    rel_path = out_path.relative_to(ROOT) if out_path.is_relative_to(ROOT) else out_path
    print(
        f"✅ Built {rel_path} ({len(parts)} modules)"
        f" — version {version} ({commit}) ({build_date})."
    )

    # 🧹 Auto-format if possible
    try:
        result = subprocess.run(
            ["poetry", "run", "poe", "fix"],  # noqa: S607
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
        description="Bundle Pocket Build into a single script.",
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

    out_path = (
        Path(args.out).expanduser().resolve()
        if getattr(args, "out", None)
        else DEFAULT_OUT_FILE
    )
    build_single_file(out_path, package_name=args.package)
    verify_compiles(out_path)

    size = out_path.stat().st_size / 1024
    print(f"📦 Output size: {size:.1f} KB")


if __name__ == "__main__":
    main()
