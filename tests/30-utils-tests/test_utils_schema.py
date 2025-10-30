# tests/30-utils-tests/test_utils_schema.py

from typing import TypedDict, cast

import pocket_build.utils_schema as mod_utils_schema
from tests.utils import make_summary


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# --- fixtures --------------------------------------------------------------


class MiniBuild(TypedDict, total=False):
    include: list[str]
    out: str
    strict_config: bool


# --- collect_msg ----------------------------------------------------


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


# --- flush_schema_aggregators ---------------------------------------


def test_flush_schema_aggregators_flushes_strict_bucket() -> None:
    # --- setup ---
    summary = make_summary(strict=True)
    agg: mod_utils_schema.SchemaErrorAggregator = cast(
        "mod_utils_schema.SchemaErrorAggregator",
        {
            mod_utils_schema.AGG_STRICT_WARN: {
                "dry-run": {
                    "msg": "Ignored config key(s) {keys} {ctx}",
                    "contexts": ["in build #1", "on build #2"],
                },
            },
        },
    )

    # --- execute ---
    mod_utils_schema.flush_schema_aggregators(summary=summary, agg=agg)

    # --- verify ---
    assert not agg[mod_utils_schema.AGG_STRICT_WARN]  # bucket should be cleared
    assert summary.valid is False
    assert len(summary.strict_warnings) == 1
    msg = summary.strict_warnings[0]
    assert "dry-run" in msg
    assert "build #1" in msg
    assert "build #2" in msg
    assert "Ignored config key(s)" in msg


def test_flush_schema_aggregators_flushes_warning_bucket() -> None:
    # --- setup ---
    summary = make_summary(strict=False)
    agg: mod_utils_schema.SchemaErrorAggregator = cast(
        "mod_utils_schema.SchemaErrorAggregator",
        {
            mod_utils_schema.AGG_WARN: {
                "root-only": {
                    "msg": "Ignored {keys} {ctx}",
                    "contexts": ["in top-level configuration"],
                },
            },
        },
    )

    # --- execute ---
    mod_utils_schema.flush_schema_aggregators(summary=summary, agg=agg)

    # --- verify ---
    assert not agg[mod_utils_schema.AGG_WARN]
    assert summary.valid is True
    assert summary.warnings == ["Ignored root-only in top-level configuration"]
    assert summary.strict_warnings == []
    assert summary.errors == []


def test_flush_schema_aggregators_cleans_context_prefixes() -> None:
    # --- setup ---
    summary = make_summary(strict=True)
    agg: mod_utils_schema.SchemaErrorAggregator = cast(
        "mod_utils_schema.SchemaErrorAggregator",
        {
            mod_utils_schema.AGG_STRICT_WARN: {
                "noop": {
                    "msg": "Ignored {keys} {ctx}",
                    "contexts": ["in build #3", "on build #4", "build #5"],
                },
            },
        },
    )

    # --- execute ---
    mod_utils_schema.flush_schema_aggregators(summary=summary, agg=agg)

    # --- verify ---
    assert not agg[mod_utils_schema.AGG_STRICT_WARN]
    msg = summary.strict_warnings[0]
    # Context prefixes 'in' and 'on' should not be duplicated
    assert msg == "Ignored noop in build #3, build #4, build #5"
