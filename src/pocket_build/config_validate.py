# src/pocket_build/config_validate.py


from typing import Any

from .constants import DEFAULT_STRICT_CONFIG
from .types import BuildConfigInput, RootConfigInput
from .utils_schema import (
    SchemaErrorAggregator,
    ValidationSummary,
    check_schema_conformance,
    collect_msg,
    flush_schema_aggregators,
    warn_keys_once,
)
from .utils_types import cast_hint, schema_from_typeddict

# --- constants ------------------------------------------------------

DRYRUN_KEYS = {"dry-run", "dry_run", "dryrun", "no-op", "no_op", "noop"}
DRYRUN_MSG = (
    "Ignored config key(s) {keys} {ctx}: this tool has no config option for it. "
    "Use the CLI flag '--dry-run' instead."
)

ROOT_ONLY_KEYS = {"watch_interval"}
ROOT_ONLY_MSG = "Ignored {keys} {ctx}: these options only apply at the root level."


# ---------------------------------------------------------------------------
# main validator
# ---------------------------------------------------------------------------


def validate_config(
    parsed_cfg: dict[str, Any], *, strict: bool | None = None
) -> ValidationSummary:
    """Validate normalized config. Returns True if valid.

    strict=True  →  warnings become fatal, but still listed separately
    strict=False →  warnings remain non-fatal

    The `strict_config` key in the root config (and optionally in each build)
    controls strictness. CLI flags are not considered.

    Returns a ValidationSummary object.
    """
    summary = ValidationSummary(
        valid=True,
        errors=[],
        strict_warnings=[],
        warnings=[],
        strict=DEFAULT_STRICT_CONFIG,
    )
    agg: SchemaErrorAggregator = {}

    def set_valid_and_return(flush: bool = True) -> ValidationSummary:
        if flush:
            flush_schema_aggregators(summary, agg)
        summary.valid = not summary.errors and not summary.strict_warnings
        return summary

    root_strict: bool = summary.strict
    # --- Determine strictness from root config ---
    strict_from_root: Any = parsed_cfg.get("strict_config")
    if strict is None and isinstance(strict_from_root, bool):
        root_strict = strict_from_root
    if root_strict:
        summary.strict = True
    strict_config: bool = root_strict

    # --- Validate root-level keys ---
    ROOT_SCHEMA = schema_from_typeddict(RootConfigInput)
    prewarn_root: set[str] = set()
    ok, found = warn_keys_once(
        strict_config,
        "dry-run",
        DRYRUN_KEYS,
        parsed_cfg,
        "in top-level configuration",
        DRYRUN_MSG,
        summary,
        agg=agg,
    )
    prewarn_root |= found

    ok = check_schema_conformance(
        strict_config,
        parsed_cfg,
        ROOT_SCHEMA,
        "in top-level configuration",
        summary=summary,
        prewarn=prewarn_root,
        ignore_keys={"builds"},
    )
    if not ok and not (summary.errors or summary.strict_warnings):
        collect_msg(True, "Top-level configuration invalid.", summary, is_error=True)

    # --- Validate builds structure ---
    builds_raw: Any = parsed_cfg.get("builds", [])
    if not isinstance(builds_raw, list):
        collect_msg(True, "`builds` must be a list of builds.", summary, is_error=True)
        return set_valid_and_return()

    if not builds_raw:
        msg = "No `builds` key defined"
        if not (summary.errors or summary.strict_warnings):
            msg = msg + ";  continuing with empty configuration"
        else:
            msg = msg + "."
        collect_msg(
            False,
            msg,
            summary,
        )
        return set_valid_and_return()

    builds = cast_hint(list[Any], builds_raw)
    BUILD_SCHEMA = schema_from_typeddict(BuildConfigInput)

    for i, b in enumerate(builds):
        if not isinstance(b, dict):
            collect_msg(
                True,
                f"Build #{i + 1} must be an object"
                " with named keys (not a list or value)",
                summary,
                is_error=True,
            )
            summary.valid = False
            continue
        b = cast_hint(dict[str, Any], b)

        # inherit root strictness unless overridden below
        strict_config = root_strict
        strict_from_build: Any = b.get("strict_config")
        if strict is None and isinstance(strict_from_build, bool):
            strict_config = strict_from_build

        prewarn_build: set[str] = set()
        ok, found = warn_keys_once(
            strict_config,
            "dry-run",
            DRYRUN_KEYS,
            b,
            f"in build #{i + 1}",
            DRYRUN_MSG,
            summary,
            agg=agg,
        )
        prewarn_build |= found

        ok, found = warn_keys_once(
            strict_config,
            "root-only",
            ROOT_ONLY_KEYS,
            b,
            f"in build #{i + 1}",
            ROOT_ONLY_MSG,
            summary,
            agg=agg,
        )
        prewarn_build |= found

        ok = check_schema_conformance(
            strict_config,
            b,
            BUILD_SCHEMA,
            f"in build #{i + 1}",
            summary=summary,
            prewarn=prewarn_build,
        )
        if not ok and not (summary.errors or summary.strict_warnings):
            collect_msg(True, f"Build #{i + 1} schema invalid", summary, is_error=True)
            summary.valid = False

    # --- finalize result ---
    return set_valid_and_return()
