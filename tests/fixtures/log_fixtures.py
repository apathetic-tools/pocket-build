"""Reusable fixtures for testing the Apathetic logger system."""

import uuid

import pytest

import pocket_build.logs as mod_logs
from tests.utils import make_test_trace, patch_everywhere


TEST_TRACE = make_test_trace(icon="📏")


def _suffix() -> str:
    return "_" + uuid.uuid4().hex[:6]


@pytest.fixture
def direct_logger() -> mod_logs.AppLogger:
    """Create a brand-new AppLogger with no shared state.

    Only for testing the logger itself.

    This fixture does NOT affect get_logger() or global state —
    it’s just a clean logger instance for isolated testing.
    """
    # Give each test’s logger a unique name for debug clarity
    name = f"test_logger{_suffix()}"
    return mod_logs.AppLogger(name, enable_color=False)


@pytest.fixture
def module_logger(monkeypatch: pytest.MonkeyPatch) -> mod_logs.AppLogger:
    """Replace get_logger() everywhere with a new isolated instance.

    Ensures all modules (build, config, etc.) calling get_logger()
    will use this test logger for the duration of the test.

    Automatically reverts after test completion.
    """
    new_logger = mod_logs.AppLogger(f"isolated_logger{_suffix()}", enable_color=False)
    patch_everywhere(monkeypatch, mod_logs, "get_logger", lambda: new_logger)
    TEST_TRACE(
        "module_logger fixture",
        f"id={id(new_logger)}",
        f"level={new_logger.level_name}",
        f"handlers={[type(h).__name__ for h in new_logger.handlers]}",
    )
    return new_logger
