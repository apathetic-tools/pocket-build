# tests/test_cli.py
"""Tests for package.cli (package and standalone versions)."""

import json
from pathlib import Path

import pytest

import pocket_build.cli as mod_cli
import pocket_build.meta as mod_meta


def test_main_no_config(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Should print a warning and return exit code 1 when config is missing."""
    # --- patch and execute ---
    monkeypatch.chdir(tmp_path)
    code = mod_cli.main([])

    # --- verify ---
    assert code == 1
    captured = capsys.readouterr()
    out = (captured.out + captured.err).lower()
    assert "No build config".lower() in out


def test_main_with_config(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Should detect config, run one build, and exit cleanly."""
    # --- setup ---
    config = tmp_path / f".{mod_meta.PROGRAM_SCRIPT}.json"
    config.write_text(json.dumps({"builds": [{"include": [], "out": "dist"}]}))

    # --- patch and execute ---
    monkeypatch.chdir(tmp_path)
    code = mod_cli.main([])

    # --- verify ---
    out = capsys.readouterr().out.lower()
    assert code == 0
    assert "Build completed".lower() in out


def test_dry_run_creates_no_files(tmp_path: Path) -> None:
    # --- setup ---
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "foo.txt").write_text("data")

    config = tmp_path / f".{mod_meta.PROGRAM_SCRIPT}.json"
    config.write_text('{"builds": [{"include": ["src/**"], "out": "dist"}]}')

    # --- execute ---
    code = mod_cli.main(["--config", str(config), "--dry-run"])

    # --- verify ---
    assert code == 0
    assert not (tmp_path / "dist").exists()


def test_main_with_custom_config(tmp_path: Path) -> None:
    # --- setup ---
    config = tmp_path / f".{mod_meta.PROGRAM_SCRIPT}.json"
    config.write_text('{"builds": [{"include": ["src"], "out": "dist"}]}')

    # --- execute ---
    code = mod_cli.main(["--config", str(config)])

    # --- verify ---
    assert code == 0


def test_main_invalid_config(tmp_path: Path) -> None:
    # --- setup ---
    bad = tmp_path / f".{mod_meta.PROGRAM_SCRIPT}.json"
    bad.write_text("{not valid json}")

    # --- execute ---
    code = mod_cli.main(["--config", str(bad)])

    # --- verify ---
    assert code == 1


# --------------------------------------------------------------------------- #
# Missing includes warning/error tests (respecting strict_config)
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("config_content", "cli_args", "expect_exit", "expect_msg", "description"),
    [  # pyright: ignore[reportUnknownArgumentType]
        # Explicit include:[] means intentional empty - no warning
        (
            {"builds": [{"include": [], "out": "dist"}]},
            [],
            0,
            None,
            "explicit_include_empty",
        ),
        # Empty list shorthand [] parses to None, triggers "no config" error
        (
            "[]",
            [],
            1,
            "No build config",
            "empty_list_shorthand",
        ),
        # Empty builds with strict_config=false - warn only
        (
            {"strict_config": False, "builds": []},
            [],
            0,
            "No include patterns",
            "empty_builds_strict_false",
        ),
        # Empty builds with strict_config=true - error
        (
            {"strict_config": True, "builds": []},
            [],
            1,
            "No include patterns",
            "empty_builds_strict_true",
        ),
        # Build missing include, strict_config=false - warn only
        (
            {"strict_config": False, "builds": [{"out": "dist"}]},
            [],
            0,
            "No include patterns",
            "missing_include_strict_false",
        ),
        # Build missing include, strict_config=true - error
        (
            {"strict_config": True, "builds": [{"out": "dist"}]},
            [],
            1,
            "No include patterns",
            "missing_include_strict_true",
        ),
        # Build overrides root strict=true to false - warn only
        (
            {
                "strict_config": True,
                "builds": [{"strict_config": False, "out": "dist"}],
            },
            [],
            0,
            "No include patterns",
            "build_override_to_false",
        ),
        # Build overrides root strict=false to true - error
        (
            {
                "strict_config": False,
                "builds": [{"strict_config": True, "out": "dist"}],
            },
            [],
            1,
            "No include patterns",
            "build_override_to_true",
        ),
        # Missing include but CLI provides --include - no warning
        (
            {"builds": [{"out": "dist"}]},
            ["--include", "src/**"],
            0,
            None,
            "cli_include_provided",
        ),
        # Missing include but CLI provides --add-include - no warning
        (
            {"builds": [{"out": "dist"}]},
            ["--add-include", "src/**"],
            0,
            None,
            "cli_add_include_provided",
        ),
        # Empty object {} parses to None, triggers "no config" error
        (
            "{}",
            [],
            1,
            "No build config",
            "empty_object_config",
        ),
        # Config with only log_level, no builds - error (default strict=true)
        (
            {"log_level": "debug"},
            [],
            1,
            "No include patterns",
            "only_log_level",
        ),
        # Multiple builds, one has includes - no warning
        (
            {
                "builds": [
                    {"include": ["src/**"], "out": "dist1"},
                    {"out": "dist2"},  # This one missing, but first has includes
                ]
            },
            [],
            0,
            None,
            "mixed_builds_one_has_includes",
        ),
    ],
    ids=lambda x: x if isinstance(x, str) and not x.startswith("{") else "",
)
def test_missing_includes_behavior(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    config_content: dict[str, object] | str,
    cli_args: list[str],
    expect_exit: int,
    expect_msg: str | None,
    description: str,
) -> None:
    """Test missing includes warning/error with various configurations."""
    # --- setup ---
    config = tmp_path / f".{mod_meta.PROGRAM_SCRIPT}.json"
    if isinstance(config_content, str):
        config.write_text(config_content)
    else:
        config.write_text(json.dumps(config_content))

    # Create dummy src directory for CLI include tests
    if "--include" in cli_args or "--add-include" in cli_args:
        src = tmp_path / "src"
        src.mkdir()
        (src / "test.txt").write_text("data")

    # --- execute ---
    monkeypatch.chdir(tmp_path)
    code = mod_cli.main(cli_args)

    # --- verify ---
    assert code == expect_exit, f"Failed: {description}"
    captured = capsys.readouterr()
    combined = (captured.out + captured.err).lower()

    if expect_msg:
        assert expect_msg.lower() in combined, (
            f"Failed: {description} - expected message not found"
        )
    else:
        assert "No include patterns".lower() not in combined, (
            f"Failed: {description} - unexpected warning"
        )
