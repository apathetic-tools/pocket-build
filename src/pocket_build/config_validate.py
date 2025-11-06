# src/pocket_build/config_validate.py


from typing import Any

from .config_types import BuildConfig, RootConfig
from .constants import DEFAULT_STRICT_CONFIG
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

# Field-specific type examples for better error messages
# Dict format: {field_pattern: example_value}
# Wildcard patterns (with *) are supported for matching multiple fields
FIELD_EXAMPLES: dict[str, str] = {
    "root.builds.*.include": '["src/", "lib/"]',
    "root.builds.*.out": '"dist"',
    "root.watch_interval": "1.5",
    "root.log_level": '"debug"',
    "root.strict_config": "true",
}


# ---------------------------------------------------------------------------
# main validator
# ---------------------------------------------------------------------------


def _set_valid_and_return(
    *,
    flush: bool = True,
    summary: ValidationSummary,  # could be modified
    agg: SchemaErrorAggregator,  # could be modified
) -> ValidationSummary:
    if flush:
        flush_schema_aggregators(summary=summary, agg=agg)
    summary.valid = not summary.errors and not summary.strict_warnings
    return summary


def _validate_root(
    parsed_cfg: dict[str, Any],
    *,
    strict_arg: bool | None,
    summary: ValidationSummary,  # modified
    agg: SchemaErrorAggregator,  # modified
) -> ValidationSummary | None:
    strict_config: bool = summary.strict
    # --- Determine strictness from arg or root config or default ---
    strict_from_root: Any = parsed_cfg.get("strict_config")
    if strict_arg is not None and strict_arg:
        strict_config = strict_arg
    elif strict_arg is None and isinstance(strict_from_root, bool):
        strict_config = strict_from_root

    if strict_config:
        summary.strict = True

    # --- Validate root-level keys ---
    root_schema = schema_from_typeddict(RootConfig)
    prewarn_root: set[str] = set()
    ok, found = warn_keys_once(
        "dry-run",
        DRYRUN_KEYS,
        parsed_cfg,
        "in top-level configuration",
        DRYRUN_MSG,
        strict_config=strict_config,
        summary=summary,
        agg=agg,
    )
    prewarn_root |= found

    ok = check_schema_conformance(
        parsed_cfg,
        root_schema,
        "in top-level configuration",
        strict_config=strict_config,
        summary=summary,
        prewarn=prewarn_root,
        ignore_keys={"builds"},
        base_path="root",
        field_examples=FIELD_EXAMPLES,
    )
    if not ok and not (summary.errors or summary.strict_warnings):
        collect_msg(
            "Top-level configuration invalid.",
            strict=True,
            summary=summary,
            is_error=True,
        )

    return None


def _validate_builds(
    parsed_cfg: dict[str, Any],
    *,
    strict_arg: bool | None,
    summary: ValidationSummary,  # modified
    agg: SchemaErrorAggregator,  # modified
) -> ValidationSummary | None:
    root_strict = summary.valid
    builds_raw: Any = parsed_cfg.get("builds", [])
    if not isinstance(builds_raw, list):
        collect_msg(
            "`builds` must be a list of builds.",
            strict=True,
            summary=summary,
            is_error=True,
        )
        return _set_valid_and_return(summary=summary, agg=agg)

    if not builds_raw:
        msg = "No `builds` key defined"
        if not (summary.errors or summary.strict_warnings):
            msg = msg + ";  continuing with empty configuration"
        else:
            msg = msg + "."
        collect_msg(
            msg,
            strict=False,
            summary=summary,
        )
        return _set_valid_and_return(summary=summary, agg=agg)

    builds = cast_hint(list[Any], builds_raw)
    build_schema = schema_from_typeddict(BuildConfig)

    for i, b in enumerate(builds):
        if not isinstance(b, dict):
            collect_msg(
                f"Build #{i + 1} must be an object"
                " with named keys (not a list or value)",
                strict=True,
                summary=summary,
                is_error=True,
            )
            summary.valid = False
            continue
        b_dict = cast_hint(dict[str, Any], b)

        # strict from arg, build, or root
        strict_config = root_strict
        strict_from_build: Any = b_dict.get("strict_config")
        if strict_arg is not None:
            strict_config = strict_arg
        elif strict_arg is None and isinstance(strict_from_build, bool):
            strict_config = strict_from_build

        prewarn_build: set[str] = set()
        ok, found = warn_keys_once(
            "dry-run",
            DRYRUN_KEYS,
            b_dict,
            f"in build #{i + 1}",
            DRYRUN_MSG,
            strict_config=strict_config,
            summary=summary,
            agg=agg,
        )
        prewarn_build |= found

        ok, found = warn_keys_once(
            "root-only",
            ROOT_ONLY_KEYS,
            b_dict,
            f"in build #{i + 1}",
            ROOT_ONLY_MSG,
            strict_config=strict_config,
            summary=summary,
            agg=agg,
        )
        prewarn_build |= found

        ok = check_schema_conformance(
            b_dict,
            build_schema,
            f"in build #{i + 1}",
            strict_config=strict_config,
            summary=summary,
            prewarn=prewarn_build,
            base_path="root.builds.*",
            field_examples=FIELD_EXAMPLES,
        )
        if not ok and not (summary.errors or summary.strict_warnings):
            collect_msg(
                f"Build #{i + 1} schema invalid",
                strict=True,
                summary=summary,
                is_error=True,
            )
            summary.valid = False

    return None


def validate_config(
    parsed_cfg: dict[str, Any],
    *,
    strict: bool | None = None,
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

    # --- Validate root structure ---
    ret = _validate_root(
        parsed_cfg,
        strict_arg=strict,
        summary=summary,
        agg=agg,
    )
    if ret is not None:
        return ret

    # --- Validate builds structure ---
    ret = _validate_builds(parsed_cfg, strict_arg=strict, summary=summary, agg=agg)
    if ret is not None:
        return ret

    # --- finalize result ---
    return _set_valid_and_return(
        summary=summary,
        agg=agg,
    )
