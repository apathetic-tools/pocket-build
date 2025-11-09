# tests/5_core/test_can_run_configless.py

from argparse import Namespace

import pocket_build.config as mod_config


def test_can_run_configless_with_include() -> None:
    """Should return True when --include is present."""
    args = Namespace(
        include=["src/**/*.py"],
        add_include=None,
        positional_include=None,
        positional_out=None,
    )
    assert mod_config.can_run_configless(args) is True


def test_can_run_configless_with_add_include() -> None:
    """Should return True when --add-include is present."""
    args = Namespace(
        include=None,
        add_include=["tests/**/*.py"],
        positional_include=None,
        positional_out=None,
    )
    assert mod_config.can_run_configless(args) is True


def test_can_run_configless_with_positional_include() -> None:
    """Should return True when positional include is present."""
    args = Namespace(
        include=None,
        add_include=None,
        positional_include=["docs/**"],
        positional_out=None,
    )
    assert mod_config.can_run_configless(args) is True


def test_can_run_configless_with_positional_out() -> None:
    """Should return True when positional_out is present."""
    args = Namespace(
        include=None,
        add_include=None,
        positional_include=None,
        positional_out="build/",
    )
    assert mod_config.can_run_configless(args) is True


def test_can_run_configless_with_multiple_options() -> None:
    """Should return True when multiple options are present."""
    args = Namespace(
        include=["src/**"],
        add_include=["tests/**"],
        positional_include=None,
        positional_out=None,
    )
    assert mod_config.can_run_configless(args) is True


def test_can_run_configless_with_all_options() -> None:
    """Should return True when all options are present."""
    args = Namespace(
        include=["src/**"],
        add_include=["tests/**"],
        positional_include=["docs/**"],
        positional_out="build/",
    )
    assert mod_config.can_run_configless(args) is True


def test_can_run_configless_with_no_options() -> None:
    """Should return False when no options are present."""
    args = Namespace(
        include=None,
        add_include=None,
        positional_include=None,
        positional_out=None,
    )
    assert mod_config.can_run_configless(args) is False


def test_can_run_configless_with_empty_include() -> None:
    """Should return False when include is an empty list."""
    args = Namespace(
        include=[],
        add_include=None,
        positional_include=None,
        positional_out=None,
    )
    assert mod_config.can_run_configless(args) is False


def test_can_run_configless_with_empty_add_include() -> None:
    """Should return False when add_include is an empty list."""
    args = Namespace(
        include=None,
        add_include=[],
        positional_include=None,
        positional_out=None,
    )
    assert mod_config.can_run_configless(args) is False


def test_can_run_configless_with_empty_positional_include() -> None:
    """Should return False when positional_include is an empty list."""
    args = Namespace(
        include=None,
        add_include=None,
        positional_include=[],
        positional_out=None,
    )
    assert mod_config.can_run_configless(args) is False


def test_can_run_configless_with_empty_positional_out() -> None:
    """Should return False when positional_out is an empty string."""
    args = Namespace(
        include=None,
        add_include=None,
        positional_include=None,
        positional_out="",
    )
    assert mod_config.can_run_configless(args) is False


def test_can_run_configless_missing_attributes() -> None:
    """Should return False when some attributes are missing from Namespace."""
    args = Namespace()
    assert mod_config.can_run_configless(args) is False


def test_can_run_configless_partial_missing_attributes() -> None:
    """Should return True when only some required attributes are missing but
    one present attribute has a truthy value."""
    args = Namespace(include=["src/**"])
    # Only 'include' is set, others don't exist
    assert mod_config.can_run_configless(args) is True


def test_can_run_configless_with_zero() -> None:
    """Should return False when a numeric value is 0."""
    args = Namespace(
        include=None,
        add_include=None,
        positional_include=None,
        positional_out=0,
    )
    assert mod_config.can_run_configless(args) is False


def test_can_run_configless_with_false() -> None:
    """Should return False when a value is explicitly False."""
    args = Namespace(
        include=None,
        add_include=None,
        positional_include=None,
        positional_out=False,
    )
    assert mod_config.can_run_configless(args) is False
