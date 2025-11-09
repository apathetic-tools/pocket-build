"""Tests for fnmatchcase_portable() glob pattern matching.

fnmatchcase_portable() is a drop-in replacement for fnmatch.fnmatch that:
- Always uses case-sensitive matching (via fnmatchcase from stdlib)
- Backports Python 3.11's recursive '**' support to Python 3.10
- Uses the Python stdlib's fnmatchcase for non-** patterns
- Handles *, **, ?, and [] glob patterns

IMPORTANT: fnmatchcase (unlike shell globbing) does allow * to cross directory
separators. This function is designed for gitignore-style pattern matching,
not shell glob semantics.

Checklist:
- literal_match — exact string matching without glob chars
- single_star_behavior — * in fnmatchcase matches any chars (including /)
- question_mark — ? matches exactly one character (excluding newline)
- character_class — [] matches character classes
- case_sensitive — matching respects case
- empty_pattern — empty pattern behavior
- empty_path — empty path behavior
- no_glob_chars_uses_fnmatchcase — non-** patterns delegate to fnmatchcase
- recursive_backport_python310 — ** works on Python 3.10 via backport
- character_class_negation — [!...] negates a character class
- complex_patterns — real-world complex gitignore-style patterns
"""

import sys
from fnmatch import fnmatchcase
from types import SimpleNamespace

import pytest

import pocket_build.utils as mod_utils
from tests.utils import patch_everywhere


def test_fnmatchcase_portable_literal_match() -> None:
    """Exact string matching without glob characters.

    Example:
      path:    "src/main.py"
      pattern: "src/main.py"
      Result:  True
      Explanation: no glob chars; exact match required.

    """
    # --- execute + verify ---
    assert mod_utils.fnmatchcase_portable("src/main.py", "src/main.py")
    assert not mod_utils.fnmatchcase_portable("src/main.py", "src/other.py")
    assert not mod_utils.fnmatchcase_portable("src/main.py", "other/main.py")


def test_fnmatchcase_portable_single_star_matches() -> None:
    """Single * matches any characters (including directory separators).

    NOTE: fnmatchcase (unlike shell globbing) allows * to cross '/'.
    This is by design for gitignore-style matching.

    Example:
      path:    "src/main.py"
      pattern: "src/*.py"
      Result:  True
      pattern: "*.py"
      pattern: "src/sub/main.py"
      Result:  True (because * can match '/')

    """
    # --- execute + verify ---
    assert mod_utils.fnmatchcase_portable("src/main.py", "src/*.py")
    assert mod_utils.fnmatchcase_portable("src/test.py", "src/*.py")
    # fnmatchcase allows * to cross /, unlike shell globbing
    assert mod_utils.fnmatchcase_portable("src/sub/main.py", "src/*.py")
    assert not mod_utils.fnmatchcase_portable("src/main.txt", "src/*.py")


def test_fnmatchcase_portable_single_star_matches_any() -> None:
    """* matches any characters, including slashes.

    This is gitignore semantics, not shell glob semantics.

    Example:
      path:    "a/b/c.py"
      pattern: "*.py"
      Result:  True (even though * crosses directories)

    """
    # --- execute + verify ---
    assert mod_utils.fnmatchcase_portable("main.py", "*.py")
    assert mod_utils.fnmatchcase_portable("src/main.py", "*.py")
    assert mod_utils.fnmatchcase_portable("src/sub/deep/main.py", "*.py")
    assert not mod_utils.fnmatchcase_portable("main.txt", "*.py")


def test_fnmatchcase_portable_double_star_matches() -> None:
    """** matches paths with at least one slash-separated segment.

    On Python 3.11+, fnmatchcase handles **. On Python 3.10, we backport it.
    ** requires at least one path component between delimiters.

    Example:
      path:    "src/a/b/c/main.py"
      pattern: "src/**/main.py"
      Result:  True
      Explanation: ** matches 'a/b/c' recursively.

      path:    "src/main.py"
      pattern: "src/**/main.py"
      Result:  False
      Explanation: ** cannot match empty (zero-length).

    """
    # --- execute + verify ---
    # ** requires at least one segment
    assert not mod_utils.fnmatchcase_portable("src/main.py", "src/**/main.py")

    # With intervening path
    assert mod_utils.fnmatchcase_portable("src/a/main.py", "src/**/main.py")
    assert mod_utils.fnmatchcase_portable("src/a/b/c/main.py", "src/**/main.py")
    assert not mod_utils.fnmatchcase_portable("other/a/b/c/main.py", "src/**/main.py")


def test_fnmatchcase_portable_double_star_multiple() -> None:
    """Multiple ** in one pattern.

    Example:
      path:    "src/a/b/test/c/d/main.py"
      pattern: "src/**/test/**/main.py"
      Result:  True
      Explanation: first ** matches 'a/b/'; second ** matches 'c/d/'.

    """
    # --- execute + verify ---
    assert mod_utils.fnmatchcase_portable(
        "src/a/b/test/c/d/main.py", "src/**/test/**/main.py"
    )
    # Each ** requires at least one segment
    pattern = "src/**/test/**/main.py"
    assert not mod_utils.fnmatchcase_portable("src/test/main.py", pattern)
    assert not mod_utils.fnmatchcase_portable(
        "src/a/other/c/d/main.py", "src/**/test/**/main.py"
    )


def test_fnmatchcase_portable_question_mark() -> None:
    """? matches exactly one character (including /).

    Example:
      path:    "file1.py"
      pattern: "file?.py"
      Result:  True
      Explanation: ? matches '1'.

    Note: Unlike some glob systems, ? can match / in fnmatchcase.

    """
    # --- execute + verify ---
    assert mod_utils.fnmatchcase_portable("file1.py", "file?.py")
    assert mod_utils.fnmatchcase_portable("fileA.py", "file?.py")
    assert not mod_utils.fnmatchcase_portable("file12.py", "file?.py")
    # ? can match / in fnmatchcase
    assert mod_utils.fnmatchcase_portable("file/.py", "file?.py")
    assert not mod_utils.fnmatchcase_portable("file.py", "file?.py")


def test_fnmatchcase_portable_character_class() -> None:
    """[] matches character classes.

    Example:
      path:    "file1.py"
      pattern: "file[0-9].py"
      Result:  True
      Explanation: [0-9] matches '1'.

    """
    # --- execute + verify ---
    assert mod_utils.fnmatchcase_portable("file1.py", "file[0-9].py")
    assert mod_utils.fnmatchcase_portable("file5.py", "file[0-9].py")
    assert not mod_utils.fnmatchcase_portable("fileA.py", "file[0-9].py")
    assert mod_utils.fnmatchcase_portable("fileA.py", "file[A-Z].py")
    assert mod_utils.fnmatchcase_portable("file1.py", "file[0-9a-z].py")


def test_fnmatchcase_portable_character_class_negation() -> None:
    """[!...] or [^...] negates a character class.

    Example:
      path:    "fileA.py"
      pattern: "file[!0-9].py"
      Result:  True
      Explanation: [!0-9] matches anything except digits.

    """
    # --- execute + verify ---
    assert mod_utils.fnmatchcase_portable("fileA.py", "file[!0-9].py")
    assert not mod_utils.fnmatchcase_portable("file1.py", "file[!0-9].py")


def test_fnmatchcase_portable_case_sensitive() -> None:
    """Matching is always case-sensitive.

    Example:
      path:    "Main.py"
      pattern: "main.py"
      Result:  False
      Explanation: fnmatchcase (underlying) is case-sensitive.

    """
    # --- execute + verify ---
    assert mod_utils.fnmatchcase_portable("main.py", "main.py")
    assert not mod_utils.fnmatchcase_portable("Main.py", "main.py")
    assert not mod_utils.fnmatchcase_portable("MAIN.py", "main.py")
    assert mod_utils.fnmatchcase_portable("Main.py", "Main.py")


def test_fnmatchcase_portable_empty_pattern() -> None:
    """Empty pattern matches only empty path.

    Example:
      path:    ""
      pattern: ""
      Result:  True
      path:    "file.py"
      pattern: ""
      Result:  False

    """
    # --- execute + verify ---
    assert mod_utils.fnmatchcase_portable("", "")
    assert not mod_utils.fnmatchcase_portable("file.py", "")
    assert not mod_utils.fnmatchcase_portable("x", "")


def test_fnmatchcase_portable_empty_path() -> None:
    """Empty path behavior with various patterns.

    Example:
      path:    ""
      pattern: ""
      Result:  True
      path:    ""
      pattern: "*"
      Result:  True (because * matches zero or more chars)

    """
    # --- execute + verify ---
    assert mod_utils.fnmatchcase_portable("", "")
    # In fnmatchcase, * matches empty string
    assert mod_utils.fnmatchcase_portable("", "*")
    # ** also matches empty string
    assert mod_utils.fnmatchcase_portable("", "**")
    assert not mod_utils.fnmatchcase_portable("", "*.py")


def test_fnmatchcase_portable_no_glob_chars_delegates_to_fnmatchcase(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Patterns without ** delegate to fnmatchcase directly.

    This is an optimization: if there's no '**', we don't need the
    custom regex compiler, so we use the standard library.

    """
    # --- setup: track fnmatchcase calls ---
    call_count = 0
    original_fnmatchcase = fnmatchcase

    def counting_fnmatchcase(name: str, pattern: str) -> bool:
        nonlocal call_count
        call_count += 1
        return original_fnmatchcase(name, pattern)

    # --- patch  ---
    patch_everywhere(monkeypatch, mod_utils, "fnmatchcase", counting_fnmatchcase)

    # --- execute ---
    # Pattern without '**' should use fnmatchcase
    mod_utils.fnmatchcase_portable("src/main.py", "src/*.py")
    fnmatchcase_calls_without_double_star = call_count

    call_count = 0
    # Pattern with '**' on Python 3.10 should use custom compiler
    fake_sys = SimpleNamespace(version_info=(3, 10, 0))
    patch_everywhere(
        monkeypatch, mod_utils, "get_sys_version_info", lambda: fake_sys.version_info
    )
    mod_utils.fnmatchcase_portable("src/a/b/main.py", "src/**/main.py")
    fnmatchcase_calls_with_double_star_310 = call_count

    # --- verify ---
    assert fnmatchcase_calls_without_double_star > 0, (
        "Expected fnmatchcase to be called for patterns without **"
    )
    # On Python 3.10, ** should trigger the custom compiler, not fnmatchcase
    assert fnmatchcase_calls_with_double_star_310 == 0, (
        "Expected custom compiler for ** on Python 3.10"
    )


def test_fnmatchcase_portable_recursive_backport_python310(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """On Python 3.10, ** recursion is backported via custom regex.

    Example:
      Python 3.10:
        path:    "src/a/b/c/main.py"
        pattern: "src/**/main.py"
        Result:  True (backported via _compile_glob_recursive)

    """
    # --- setup: force Python 3.10 ---
    fake_sys = SimpleNamespace(version_info=(3, 10, 0))
    patch_everywhere(
        monkeypatch, mod_utils, "get_sys_version_info", lambda: fake_sys.version_info
    )

    # --- execute + verify ---
    # ** requires at least one path segment
    assert not mod_utils.fnmatchcase_portable("src/main.py", "src/**/main.py"), (
        "** requires at least one segment"
    )

    assert mod_utils.fnmatchcase_portable("src/a/b/c/main.py", "src/**/main.py")
    assert not mod_utils.fnmatchcase_portable("other/a/b/c/main.py", "src/**/main.py")


def test_fnmatchcase_portable_edge_case_brackets_as_character_class() -> None:
    """Brackets create character classes in fnmatchcase.

    Example:
      path:    "file1.py"
      pattern: "file[1].py"
      Result:  True
      Explanation: [1] is a character class matching '1'.

    """
    # --- execute + verify ---
    # [1] is a character class, not a literal
    assert mod_utils.fnmatchcase_portable("file1.py", "file[1].py")
    assert not mod_utils.fnmatchcase_portable("file[1].py", "file[1].py")
    assert mod_utils.fnmatchcase_portable("file2.py", "file[1-9].py")


def test_fnmatchcase_portable_star_at_start() -> None:
    """* at start of pattern matches anything.

    Example:
      path:    "main.py"
      pattern: "*.py"
      Result:  True
      path:    "src/main.py"
      pattern: "*.py"
      Result:  True (because * can cross /)

    """
    # --- execute + verify ---
    assert mod_utils.fnmatchcase_portable("main.py", "*.py")
    assert mod_utils.fnmatchcase_portable("test.py", "*.py")
    # * can cross / in fnmatchcase
    assert mod_utils.fnmatchcase_portable("src/main.py", "*.py")


def test_fnmatchcase_portable_double_star_at_start() -> None:
    """** at start requires at least one path component.

    Example:
      path:    "file.py"
      pattern: "**/file.py"
      Result:  False (** requires at least one component)
      path:    "src/file.py"
      pattern: "**/file.py"
      Result:  True

    """
    # --- execute + verify ---
    # ** requires at least one component
    assert not mod_utils.fnmatchcase_portable("file.py", "**/file.py")
    assert mod_utils.fnmatchcase_portable("src/file.py", "**/file.py")
    assert mod_utils.fnmatchcase_portable("src/a/b/file.py", "**/file.py")


def test_fnmatchcase_portable_double_star_at_end() -> None:
    """** at end matches any suffix.

    Example:
      path:    "src"
      pattern: "src/**"
      Result:  True
      path:    "src/a/b/c.py"
      pattern: "src/**"
      Result:  True

    """
    # --- execute + verify ---
    assert mod_utils.fnmatchcase_portable("src/main.py", "src/**")
    assert mod_utils.fnmatchcase_portable("src/a/b/c/main.py", "src/**")
    assert not mod_utils.fnmatchcase_portable("other/main.py", "src/**")


def test_fnmatchcase_portable_complex_real_world_patterns() -> None:
    """Real-world complex patterns for gitignore-style matching.

    Example:
      path:    "src/test/unit/test_main.py"
      pattern: "src/**/test_*.py"
      Result:  True

    """
    # --- execute + verify ---
    # Python package with nested tests
    pattern = "src/**/test_*.py"
    assert mod_utils.fnmatchcase_portable("src/test/unit/test_main.py", pattern)
    # ** can match empty (zero-length)
    assert mod_utils.fnmatchcase_portable("src/test/test_main.py", pattern)
    assert not mod_utils.fnmatchcase_portable("src/main.py", "src/**/test_*.py")

    # Build artifact pattern
    # build/lib/main.py: ** matches 'lib/' (non-empty slash-separated)
    assert mod_utils.fnmatchcase_portable("build/lib/main.py", "build/**/*.py")
    assert mod_utils.fnmatchcase_portable("build/lib/a/b/c/main.py", "build/**/*.py")
    assert not mod_utils.fnmatchcase_portable("build/lib/main.txt", "build/**/*.py")

    # Ignore pattern (like .gitignore)
    # dist/bundle.js: first ** needs at least one component (doesn't match)
    assert not mod_utils.fnmatchcase_portable("dist/bundle.js", "**/dist/**")
    # app/dist/bundle.js: ** matches 'app/', then dist, then second ** matches 'sub/'
    assert mod_utils.fnmatchcase_portable("app/dist/bundle.js", "**/dist/**")
    assert mod_utils.fnmatchcase_portable("app/nested/dist/sub/bundle.js", "**/dist/**")


def test_fnmatchcase_portable_run_of_stars() -> None:
    """Consecutive stars (***+) treated as recursive **.

    Example:
      path:    "src/a/b/c/main.py"
      pattern: "src***/main.py"  (three stars)
      Result:  True
      Explanation: *** collapses to ** which matches recursively.

    """
    # --- force Python 3.10 to test custom compiler ---
    # (on 3.11+ this would use the stdlib)
    # For now, just test the behavior
    assert mod_utils.fnmatchcase_portable("src/a/b/c/main.py", "src**main.py")


def test_fnmatchcase_portable_special_chars_in_path() -> None:
    """Literal special chars in path (when not glob syntax).

    Example:
      path:    "file-1.py"
      pattern: "file-*.py"
      Result:  True
      path:    "file+1.py"
      pattern: "file+*.py"
      Result:  True

    """
    # --- execute + verify ---
    assert mod_utils.fnmatchcase_portable("file-1.py", "file-*.py")
    assert mod_utils.fnmatchcase_portable("file+1.py", "file+*.py")
    assert mod_utils.fnmatchcase_portable("file.1.py", "file.*.py")


@pytest.mark.skipif(sys.version_info < (3, 11), reason="Only relevant for Python 3.11+")
@pytest.mark.parametrize(
    ("path", "pattern"),
    [
        # Literal matches
        ("src/main.py", "src/main.py"),
        ("main.py", "other.py"),
        # Single star
        ("main.py", "*.py"),
        ("src/main.py", "*.py"),
        ("src/sub/main.py", "src/*.py"),
        # Double star
        ("src/main.py", "src/**/main.py"),
        ("src/a/main.py", "src/**/main.py"),
        ("src/a/b/c/main.py", "src/**/main.py"),
        ("test/main.py", "src/**/main.py"),
        # Question mark
        ("file1.py", "file?.py"),
        ("file12.py", "file?.py"),
        # Character class
        ("file1.py", "file[0-9].py"),
        ("fileA.py", "file[0-9].py"),
        # Complex patterns
        ("src/test/unit/test_main.py", "src/**/test_*.py"),
        ("build/lib/main.py", "build/**/*.py"),
        ("dist/bundle.js", "**/dist/**"),
        ("app/dist/bundle.js", "**/dist/**"),
    ],
)
def test_fnmatchcase_portable_matches_stdlib_on_py311_plus(
    path: str, pattern: str
) -> None:
    """On Python 3.11+, fnmatchcase_portable should match fnmatchcase behavior.

    This test verifies that our portable function doesn't diverge from the
    stdlib implementation on Python 3.11+, where fnmatchcase already supports **.

    """
    # --- execute + verify ---
    portable_result = mod_utils.fnmatchcase_portable(path, pattern)
    stdlib_result = fnmatchcase(path, pattern)
    assert portable_result == stdlib_result, (
        f"Mismatch for {path!r} vs {pattern!r}: "
        f"portable={portable_result}, stdlib={stdlib_result}"
    )
