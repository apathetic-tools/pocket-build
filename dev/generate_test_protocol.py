#!/usr/bin/env python3
"""
dev/generate_test_protocol.py
-----------------------------
Auto-generate a RuntimeLike Protocol based on the current public API of
`src/pocket_build`.

Uses AST analysis across the package to detect fully qualified type references
(e.g. pathlib.Path, pocket_build.types.BuildConfig) and generates the necessary
import statements automatically.

Output: tests/package_protocol.py
"""

from __future__ import annotations

import ast
import importlib
import importlib.util
import inspect
import sys
from pathlib import Path
from typing import Set

# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT / "src"
PKG_DIR = SRC_DIR / "pocket_build"
PKG_PATH = PKG_DIR / "__init__.py"
OUT_PATH = ROOT / "tests" / "fixtures" / "runtime_protocol.py"

# Cache stdlib modules for sanity filtering
STDLIB_MODULES: set[str] = (
    set(sys.stdlib_module_names) if hasattr(sys, "stdlib_module_names") else set()
)

HEADER = """# /tests/package_protocol.py
# ruff: noqa: E501
import argparse
import pathlib
import typing
import pocket_build.types
from typing import Union, Callable
"""


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------
def load_package():
    """Dynamically import src/pocket_build without polluting sys.path."""
    spec = importlib.util.spec_from_file_location("pocket_build", PKG_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def extract_qualified_names_from_ast(source: str) -> Set[str]:
    """Extract dotted names that look like module references, not local vars."""
    tree = ast.parse(source)
    names: Set[str] = set()

    class TypeRefVisitor(ast.NodeVisitor):
        def visit_Attribute(self, node: ast.Attribute) -> None:
            parts: list[str] = []
            current: ast.AST = node
            while isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value
            if isinstance(current, ast.Name):
                parts.append(current.id)
                full = ".".join(reversed(parts))
                # Heuristics: keep only plausible module paths
                if full.startswith(("pocket_build.", "pathlib.", "typing.")):
                    names.add(full)
            self.generic_visit(node)

        def visit_Subscript(self, node: ast.Subscript) -> None:
            self.visit(node.value)
            self.visit(node.slice)

        def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
            self.visit(node.annotation)

        def visit_arg(self, node: ast.arg) -> None:
            if node.annotation:
                self.visit(node.annotation)

    TypeRefVisitor().visit(tree)
    return names


def collect_all_qualified_names(pkg_dir: Path) -> Set[str]:
    """Parse all .py files in the package directory and extract qualified names."""
    all_names: Set[str] = set()
    for py_file in pkg_dir.glob("*.py"):
        try:
            text = py_file.read_text(encoding="utf-8")
        except Exception:
            continue
        all_names |= extract_qualified_names_from_ast(text)
    return all_names


def make_imports_from_names(qualified_names: Set[str]) -> list[str]:
    """Generate sorted import statements for known modules only."""
    imports: set[str] = set()
    for qname in qualified_names:
        parts = qname.split(".")
        if parts[0] in {"typing", "builtins"}:
            continue
        if len(parts) > 1:
            mod = ".".join(parts[:-1])
            # Sanity check: does this look like a real importable module?
            try:
                spec = importlib.util.find_spec(mod)
            except (ImportError, ValueError):
                spec = None
            if spec is not None or mod.startswith("pocket_build."):
                imports.add(f"import {mod}")
    return sorted(imports)


# ------------------------------------------------------------
# Protocol generator
# ------------------------------------------------------------
def generate_protocol() -> None:
    mod = load_package()

    # Collect all public names
    names = getattr(mod, "__all__", None)
    if not names:
        #   if not n.startswith("_")] # we need private for tests
        names = [n for n in dir(mod)]

    # Collect type references across all source files
    qualified_names = collect_all_qualified_names(PKG_DIR)
    dynamic_imports = make_imports_from_names(qualified_names)

    # --- Build file content ---
    lines: list[str] = []
    lines.append("from typing import Protocol, Any, Dict, List, Optional")
    lines.extend(dynamic_imports)
    lines.append("")
    lines.append("class RuntimeLike(Protocol):")
    lines.append('    """Auto-generated interface of the pocket_build package."""')

    for name in sorted(names):
        obj = getattr(mod, name)
        if inspect.isfunction(obj):
            try:
                sig = str(inspect.signature(obj))
            except (TypeError, ValueError):
                sig = "(...)"

            if not sig.startswith("(self") and not sig.startswith("(cls"):
                if sig == "()":
                    sig = "(self)"
                else:
                    sig = "(self, " + sig[1:]
            sig = sig.replace("NoneType", "None")
            lines.append(f"    def {name}{sig}: ...")
        elif inspect.isclass(obj):
            lines.append(f"    {name}: type")
        else:
            lines.append(f"    {name}: Any")

    content = HEADER + "\n" + "\n".join(lines) + "\n"
    OUT_PATH.write_text(content, encoding="utf-8")

    rel_out = OUT_PATH.relative_to(ROOT)
    print(
        f"✅ Generated {rel_out} with {len(names)} entries"
        f" and {len(dynamic_imports)} imports."
    )


# ------------------------------------------------------------
# Entrypoint
# ------------------------------------------------------------
if __name__ == "__main__":
    generate_protocol()
