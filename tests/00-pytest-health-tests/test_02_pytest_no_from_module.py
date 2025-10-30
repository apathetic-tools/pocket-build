# tests/00-pytest-health-tests/test_02_pytest_no_from_module.py

import ast
from pathlib import Path

import pocket_build.meta as mod_meta


def test_no_from_imports_in_tests() -> None:
    tests_dir = Path(__file__).parents[2]
    bad_files: list[Path] = []

    for path in tests_dir.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.ImportFrom)
                and node.module
                and node.module.startswith(mod_meta.PROGRAM_PACKAGE)
            ):
                bad_files.append(path)
                break  # only need one hit per file

    if bad_files:
        print(
            "\n❌ Disallowed `from " + mod_meta.PROGRAM_PACKAGE + ".<module>`"
            " imports found in test files:"
        )
        for path in bad_files:
            print(f"  - {path}")
        print(
            "Use `import "
            + mod_meta.PROGRAM_PACKAGE
            + ".<module> from mod_<module>`` instead."
        )
        xmsg = f"{len(bad_files)} test file(s) import from project directly."
        raise AssertionError(xmsg)
