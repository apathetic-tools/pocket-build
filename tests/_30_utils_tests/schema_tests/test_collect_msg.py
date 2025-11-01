# tests/30-utils-tests/test_collect_msg.py

import pocket_build.utils_schema as mod_utils_schema
from tests.utils import make_summary


def test_collect_msg_appends_to_errors_when_is_error_true() -> None:
    # --- setup ---
    summary = make_summary(strict=False)

    # --- execute ---
    mod_utils_schema.collect_msg(
        strict=False,
        msg="bad thing",
        summary=summary,
        is_error=True,
    )

    # --- verify ---
    assert summary.errors == ["bad thing"]
    assert summary.warnings == []
    assert summary.strict_warnings == []


def test_collect_msg_appends_to_strict_warnings_when_strict() -> None:
    # --- setup ---
    summary = make_summary(strict=True)

    # --- execute ---
    mod_utils_schema.collect_msg(strict=True, msg="be careful", summary=summary)

    # --- verify ---
    assert summary.strict_warnings == ["be careful"]
    assert summary.errors == []
    assert summary.warnings == []


def test_collect_msg_appends_to_warnings_when_not_strict() -> None:
    # --- setup ---
    summary = make_summary(strict=False)

    # --- execute ---
    mod_utils_schema.collect_msg(strict=False, msg="heads up", summary=summary)

    # --- verify ---
    assert summary.warnings == ["heads up"]
    assert summary.errors == []
    assert summary.strict_warnings == []


def test_collect_msg_error_always_overrides_strict_mode() -> None:
    # --- setup ---
    summary = make_summary(strict=True)

    # --- execute ---
    mod_utils_schema.collect_msg(
        strict=True,
        msg="kaboom",
        summary=summary,
        is_error=True,
    )

    # --- verify ---
    assert summary.errors == ["kaboom"]
    assert summary.strict_warnings == []
    assert summary.warnings == []
