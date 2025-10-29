# tests/test_utils.py
"""Tests for package.utils (package and standalone versions)."""

# not doing tests for has_glob_chars()

import math
import sys
from io import StringIO
from pathlib import Path

import pytest
from pytest import CaptureFixture, raises

import pocket_build.utils as mod_utils
import pocket_build.utils_types as mod_utils_types
import pocket_build.utils_using_runtime as mod_utils_runtime

# ---------------------------------------------------------------------------
# get_glob_root()
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "pattern,expected",
    [
        # Basic glob roots
        ("src/**/*.py", Path("src")),
        ("foo/bar/*.txt", Path("foo/bar")),
        ("assets/*", Path("assets")),
        ("*.md", Path(".")),
        ("**/*.js", Path(".")),
        ("no/globs/here", Path("no/globs/here")),
        ("./src/*/*.cfg", Path("src")),
        ("src\\**\\*.py", Path("src")),  # backslashes normalized
        ("a/b\\c/*", Path("a/b/c")),  # mixed separators normalized
        ("", Path(".")),
        (".", Path(".")),
        ("./", Path(".")),
        ("src/*/sub/*.py", Path("src")),
        # Escaped spaces should normalize gracefully
        ("dir\\ with\\ spaces/file.txt", Path("dir with spaces/file.txt")),
        # Multiple escaped spaces
        ("folder\\ with\\ many\\ spaces/**", Path("folder with many spaces")),
        # Escaped spaces at root (no subdirs)
        ("file\\ with\\ space.txt", Path("file with space.txt")),
        # Redundant slashes collapsed
        ("folder///deep//file.txt", Path("folder/deep/file.txt")),
    ],
)
def test_get_glob_root_extracts_static_prefix(
    pattern: str,
    expected: Path,
):
    """get_glob_root() should return the non-glob portion of a path pattern."""
    # --- execute --
    result = mod_utils_runtime.get_glob_root(pattern)

    # --- verify ---
    assert result == expected, f"{pattern!r} → {result}, expected {expected}"


# ---------------------------------------------------------------------------
# normalize_path_string()
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw, expected",
    [
        # ✅ Simple normalization
        ("src/**/*.py", "src/**/*.py"),
        ("foo/bar/*.txt", "foo/bar/*.txt"),
        ("a/b\\c/*", "a/b/c/*"),
        ("src\\**\\*.py", "src/**/*.py"),
        ("folder///subdir//file.txt", "folder/subdir/file.txt"),
        ("./src/file.txt", "./src/file.txt"),
        # ✅ Escaped spaces → normalize with warning
        ("dir\\ with\\ spaces/file.txt", "dir with spaces/file.txt"),
        ("folder\\ with\\ many\\ spaces/**", "folder with many spaces/**"),
        # ✅ Trailing whitespace trimmed
        ("  ./src/file.txt  ", "./src/file.txt"),
        # ✅ Empty / trivial
        ("", ""),
        (" ", ""),
        # ✅ Previously invalid literal backslashes → now normalize
        ("dir\\back/file.txt", "dir/back/file.txt"),
        ("foo\\bar.txt", "foo/bar.txt"),
        ("path\\to\\thing", "path/to/thing"),
        # ✅ URL-like paths (preserve protocol //)
        ("file://server//share", "file://server/share"),
        ("http://example.com//foo//bar", "http://example.com/foo/bar"),
    ],
)
def test_normalize_path_string_behavior(
    raw: str,
    expected: str,
    capsys: CaptureFixture[str],
):
    """normalize_path_string() should produce normalized cross-platform paths."""
    # --- execute ---
    result = mod_utils_runtime.normalize_path_string(raw)

    # --- verify ---
    # normalization
    assert result == expected, f"{raw!r} → {result!r}, expected {expected!r}"

    # --- if escaped spaces were present, ensure we warned once ---
    if "\\ " in raw:
        stderr = capsys.readouterr().err
        assert "Normalizing escaped spaces" in stderr
    else:
        stderr = capsys.readouterr().err
        assert stderr == ""


def test_make_includeresolved_preserves_trailing_slash() -> None:
    # --- execute --
    entry = mod_utils_types.make_includeresolved("src/", root=".", origin="test")

    # --- verify ---
    assert isinstance(entry["path"], str)
    assert entry["path"].endswith("/"), (
        f"expected trailing slash, got {entry['path']!r}"
    )


# ---------------------------------------------------------------------------
# remove_path_in_error_message()
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "inner_msg, path, expected",
    [
        # ✅ Simple case — full path
        (
            "Invalid JSONC syntax in /abs/path/config.jsonc: Expecting value",
            Path("/abs/path/config.jsonc"),
            "Invalid JSONC syntax: Expecting value",
        ),
        # ✅ Quoted path
        (
            "Invalid JSONC syntax in '/abs/path/config.jsonc': Expecting value",
            Path("/abs/path/config.jsonc"),
            "Invalid JSONC syntax: Expecting value",
        ),
        # ✅ Double-quoted path
        (
            'Invalid JSONC syntax in "/abs/path/config.jsonc": Expecting value',
            Path("/abs/path/config.jsonc"),
            "Invalid JSONC syntax: Expecting value",
        ),
        # ✅ Filename-only mention
        (
            "Invalid JSONC syntax in config.jsonc: Expecting value",
            Path("/abs/path/config.jsonc"),
            "Invalid JSONC syntax: Expecting value",
        ),
        # ✅ Path without “in” keyword
        (
            "Invalid JSONC syntax /abs/path/config.jsonc: Expecting value",
            Path("/abs/path/config.jsonc"),
            "Invalid JSONC syntax: Expecting value",
        ),
        # ✅ No path mention → unchanged
        (
            "Invalid JSONC syntax: Expecting value",
            Path("/abs/path/config.jsonc"),
            "Invalid JSONC syntax: Expecting value",
        ),
        # ✅ Redundant filename without path
        (
            "Invalid JSONC syntax in 'config.jsonc'",
            Path("/abs/path/config.jsonc"),
            "Invalid JSONC syntax",
        ),
        # ✅ Multiple spaces and dangling colons cleaned
        (
            "Invalid JSONC syntax  in /abs/path/config.jsonc  :  Expecting value",
            Path("/abs/path/config.jsonc"),
            "Invalid JSONC syntax: Expecting value",
        ),
    ],
)
def test_remove_path_in_error_message_normalizes_output(
    inner_msg: str, path: Path, expected: str
):
    """remove_path_in_error_message() should strip redundant path mentions
    and normalize punctuation and whitespace cleanly."""
    # --- execute ---
    result = mod_utils.remove_path_in_error_message(inner_msg, path)

    # --- verify ---
    assert result == expected, f"{inner_msg!r} → {result!r}, expected {expected!r}"


# ---------------------------------------------------------------------------
# plural()
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value, expected",
    [
        # ✅ Integers
        (0, "s"),
        (1, ""),
        (2, "s"),
        (999, "s"),
        (-1, "s"),  # negative counts still pluralized
        # ✅ Floats
        (0.0, "s"),
        (1.0, ""),
        (1.1, "s"),
        (math.inf, "s"),
        # ✅ Sequences and containers
        ([], "s"),
        ([1], ""),
        ([1, 2], "s"),
        ("", "s"),
        ("a", ""),
        ("abc", "s"),
        ({}, "s"),
        ({"a": 1}, ""),
        ({"a": 1, "b": 2}, "s"),
        # ✅ Custom objects with __len__()
        (type("Fake", (), {"__len__": lambda self: 1})(), ""),  # type: ignore[reportUnknownLambdaType]
        (type("Fake", (), {"__len__": lambda self: 2})(), "s"),  # type: ignore[reportUnknownLambdaType]
        # ✅ Non-countable objects
        (object(), "s"),
        (None, "s"),
    ],
)
def test_plural_behavior(value: object, expected: str) -> None:
    """plural() should append 's' for pluralizable values,
    and '' for singular ones (1 or length == 1)."""
    # --- execute ---
    result = mod_utils.plural(value)

    # --- verify ---
    assert result == expected, f"{value!r} → {result!r}, expected {expected!r}"


def test_plural_custom_len_error_fallback() -> None:
    """Objects defining __len__ that raise errors should fall back gracefully."""

    # --- setup ---
    class Weird:
        def __len__(self) -> int:
            raise TypeError("unusable len()")

    # --- execute ---
    result = mod_utils.plural(Weird())

    # --- verify ---
    assert result == "s", "Expected fallback to plural form on len() failure"


# ---------------------------------------------------------------------------
# capture_output()
# ---------------------------------------------------------------------------


def test_capture_output_captures_stdout_and_stderr() -> None:
    """stdout and stderr should be captured separately and merged together."""
    # --- setup ---
    assert sys.stdout is not None and sys.stderr is not None
    old_out, old_err = sys.stdout, sys.stderr

    # --- execute ---
    with mod_utils.capture_output() as cap:
        print("hello stdout")
        print("oops stderr", file=sys.stderr)

    # --- verify ---
    out_text = cap.stdout.getvalue()
    err_text = cap.stderr.getvalue()
    merged_text = cap.merged.getvalue()

    assert "hello stdout" in out_text
    assert "oops stderr" in err_text
    # merged should contain both in order
    assert "hello stdout" in merged_text and "oops stderr" in merged_text

    # Streams must have been restored
    assert sys.stdout is old_out
    assert sys.stderr is old_err


def test_capture_output_restores_streams_after_exception() -> None:
    """Even on exception, sys.stdout/stderr should be restored."""
    # --- setup ---
    old_out, old_err = sys.stdout, sys.stderr

    # --- execute ---
    with raises(RuntimeError):
        with mod_utils.capture_output():
            print("before boom")
            raise RuntimeError("boom")

    # --- verify ---
    assert sys.stdout is old_out
    assert sys.stderr is old_err
    # The exception should have captured output attached
    try:
        with mod_utils.capture_output():
            raise ValueError("expected fail")
    except ValueError as e:
        assert hasattr(e, "captured_output")
        captured = getattr(e, "captured_output")
        assert isinstance(captured.stdout, StringIO)
        assert isinstance(captured.stderr, StringIO)
        assert isinstance(captured.merged, StringIO)


def test_capture_output_interleaved_writes_preserve_order() -> None:
    """Merged stream should record messages in chronological order."""
    # --- execute ---
    with mod_utils.capture_output() as cap:
        print("A1", end="")  # stdout
        print("B1", end="", file=sys.stderr)
        print("A2", end="")  # stdout
        print("B2", end="", file=sys.stderr)

    # --- verify ---
    merged = cap.merged.getvalue()
    # It should appear exactly in the order written
    order = (
        merged.index("A1")
        < merged.index("B1")
        < merged.index("A2")
        < merged.index("B2")
    )
    assert order


def test_capture_output_supports_str_method_and_as_dict() -> None:
    """CapturedOutput should stringify and export all buffers cleanly."""
    # --- execute ---
    with mod_utils.capture_output() as cap:
        print("hello")
        print("err", file=sys.stderr)

    # --- verify ---
    s = str(cap)
    d = cap.as_dict()

    assert isinstance(s, str)
    assert "hello" in s and "err" in s
    assert all(k in d for k in ("stdout", "stderr", "merged"))
    assert d["stdout"].strip().startswith("hello")
