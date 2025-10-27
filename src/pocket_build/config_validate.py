# src/pocket_build/config_validate.py
from __future__ import annotations

from difflib import get_close_matches
from typing import Any, cast, get_args, get_origin

from .constants import DEFAULT_HINT_CUTOFF, DEFAULT_STRICT_CONFIG
from .types import BuildConfigInput, RootConfigInput
from .utils_types import cast_hint, safe_isinstance, schema_from_typeddict
from .utils_using_runtime import log

# --- constants ------------------------------------------------------

DRYRUN_KEYS = {"dry-run", "dry_run", "dryrun", "no-op", "no_op", "noop"}
DRYRUN_MSG = (
    "Ignored config key(s) {keys} {ctx}: this tool has no config option for it. "
    "Use the CLI flag '--dry-run' instead."
)

ROOT_ONLY_KEYS = {"watch_interval"}
ROOT_ONLY_MSG = "Ignored {keys} {ctx}: these options only apply at the root level."

# --- helpers --------------------------------------------------------


def _log_strict(strict_config: bool, msg: str) -> None:
    log("error" if strict_config else "warning", msg)


def _warn_keys_once(
    strict_config: bool,
    tag: str,
    bad_keys: set[str],
    cfg: dict[str, Any],
    context: str,
    msg: str,
) -> tuple[bool, set[str]]:
    """
    Warn once for known bad keys (e.g. dry-run, root-only).
    Returns (valid, found_keys).
    """
    # did we already warn for this tag? if so just return
    if getattr(_warn_keys_once, "_warned_tags", None) is None:
        _warn_keys_once._warned_tags = set()  # type: ignore[attr-defined]

    warned_tags: set[str] = _warn_keys_once._warned_tags  # type: ignore[attr-defined]

    valid = True
    found = bad_keys & cfg.keys()
    if found:
        if tag not in warned_tags:
            _log_strict(
                strict_config,
                f"{msg.format(keys=', '.join(sorted(found)), ctx=context)}",
            )
            warned_tags.add(tag)
        if strict_config:
            valid = False
    return valid, found


# ---------------------------------------------------------------------------
# granular schema validators (private and testable)
# ---------------------------------------------------------------------------


def _infer_type_label(expected_type: Any) -> str:
    """Return a readable label for logging (e.g. 'list[str]', 'BuildConfigInput')."""
    try:
        origin = get_origin(expected_type)
        args = get_args(expected_type)
        if origin is list and args:
            return f"list[{getattr(args[0], '__name__', repr(args[0]))}]"
        if isinstance(expected_type, type):
            return expected_type.__name__
        return str(expected_type)
    except Exception:
        return repr(expected_type)


def _validate_scalar_value(
    strict: bool,
    context: str,
    key: str,
    val: Any,
    expected_type: Any,
) -> bool:
    """Validate a single non-container value against its expected type."""
    try:
        if safe_isinstance(val, expected_type):  # self-ref guard
            return True
    except Exception:
        # Defensive fallback — e.g. weird typing generics
        fallback_type = (
            expected_type if isinstance(expected_type, type) else type(expected_type)
        )
        if isinstance(val, fallback_type):
            return True

    exp_label = _infer_type_label(expected_type)
    _log_strict(
        strict, f"{context}: key '{key}' expected {exp_label}, got {type(val).__name__}"
    )
    return False


def _validate_list_value(
    strict: bool,
    context: str,
    key: str,
    val: Any,
    subtype: Any,
) -> bool:
    """Validate a homogeneous list value, delegating to scalar/TypedDict validators."""
    if not isinstance(val, list):
        exp_label = f"list[{_infer_type_label(subtype)}]"
        _log_strict(
            strict,
            f"{context}: key '{key}' expected {exp_label}, got {type(val).__name__}",
        )
        return False

    # Treat val as a real list for static type checkers
    items = cast_hint(list[Any], val)

    # Empty list → fine, nothing to check
    if not items:
        return True

    valid = True
    for i, item in enumerate(items):
        # Detect TypedDict-like subtypes
        if (
            isinstance(subtype, type)
            and hasattr(subtype, "__annotations__")
            and hasattr(subtype, "__total__")
        ):
            if not isinstance(item, dict):
                _log_strict(
                    strict,
                    f"{context}: key '{key}[{i}]' expected dict for "
                    f"TypedDict {subtype.__name__}, got {type(item).__name__}",
                )
                valid = False
                continue
            valid &= _validate_typed_dict(
                strict, f"{context}.{key}[{i}]", item, subtype
            )
        else:
            valid &= _validate_scalar_value(
                strict, context, f"{key}[{i}]", item, subtype
            )
    return valid


def _validate_typed_dict(
    strict: bool,
    context: str,
    val: Any,
    typedict_cls: type[Any],
) -> bool:
    """Validate a dict against a TypedDict schema recursively.

    - Return False if val is not a dict
    - Recurse into its fields using _validate_scalar_value or _validate_list_value
    - Warn about unknown keys under strict=True
    """
    if not isinstance(val, dict):
        _log_strict(
            strict,
            f"{context}: expected dict for TypedDict {typedict_cls.__name__}, "
            f"got {type(val).__name__}",
        )
        return False

    schema = schema_from_typeddict(typedict_cls)
    valid = True

    for field, expected_type in schema.items():
        if field not in val:
            # Optional or missing field → not a failure
            continue

        inner_val = cast(Any, val[field])
        origin = get_origin(expected_type)
        args = get_args(expected_type)
        exp_label = _infer_type_label(expected_type)

        if origin is list:
            subtype = args[0] if args else Any
            valid &= _validate_list_value(strict, context, field, inner_val, subtype)
        elif (
            isinstance(expected_type, type)
            and hasattr(expected_type, "__annotations__")
            and hasattr(expected_type, "__total__")
        ):
            valid &= _validate_typed_dict(
                strict, f"{context}.{field}", inner_val, expected_type
            )
        else:
            val_scalar = _validate_scalar_value(
                strict, context, field, inner_val, expected_type
            )
            if not val_scalar:
                _log_strict(
                    strict,
                    f"{context}: key '{field}' expected {exp_label}, "
                    f"got {type(inner_val).__name__}",
                )
                valid = False

    # --- Unknown keys ---
    val_dict = cast(dict[str, Any], val)
    unknown: list[str] = [k for k in val_dict if k not in schema]
    if unknown:
        plural = "s" if len(unknown) > 1 else ""
        _log_strict(
            strict,
            f"{len(unknown)} unknown key{plural} {context} for "
            f"TypedDict {typedict_cls.__name__}: {', '.join(unknown)}",
        )
        if strict:
            valid = False

    return valid


def _check_schema_conformance(
    strict_config: bool,
    cfg: dict[str, Any],
    schema: dict[str, Any],
    context: str,
    prewarn: set[str] = set(),
) -> bool:
    """Coordinate type checking using specialized validators."""
    valid = True

    valid = True

    for k, expected_type in schema.items():
        if k in prewarn or k not in cfg:
            continue

        val = cfg[k]
        origin = get_origin(expected_type)
        args = get_args(expected_type)

        if origin is list:
            subtype = args[0] if args else Any
            valid &= _validate_list_value(strict_config, context, k, val, subtype)
        elif (
            isinstance(expected_type, type)
            and hasattr(expected_type, "__annotations__")
            and hasattr(expected_type, "__total__")
        ):
            # Treat as TypedDict-like
            valid &= _validate_typed_dict(
                strict_config, f"{context}.{k}", val, expected_type
            )
        else:
            valid &= _validate_scalar_value(
                strict_config, context, k, val, expected_type
            )

    # --- unknown keys ---
    unknown: list[str] = []
    hints: list[str] = []
    for k in cfg:
        if k in schema or k in prewarn:
            continue
        unknown.append(k)
        close = get_close_matches(k, schema.keys(), n=1, cutoff=DEFAULT_HINT_CUTOFF)
        if close:
            hints.append("'" + k + "' → '" + close[0] + "'")
    if unknown:
        plural = "s" if len(unknown) > 1 else ""
        msg = f"{len(unknown)} unknown key{plural} {context}: {', '.join(unknown)}"
        if hints:
            msg += "\nHint: did you mean " + ", ".join(hints) + "?"
        _log_strict(strict_config, msg)
        if strict_config:
            valid = False

    return valid


# --- main validator ------------------------------------------------


def validate_config(parsed_cfg: dict[str, Any], *, strict: bool | None = None) -> bool:
    """Validate normalized config. Returns True if valid.

    strict=True  →  type errors and warnings both cause failure
    strict=False →  type errors still cause failure, but warnings are logged only

    The `strict_config` key in the root config (and optionally in each build)
    controls strictness. CLI flags are not considered.
    """
    valid = True

    root_strict: bool = strict if strict is not None else DEFAULT_STRICT_CONFIG
    # --- Determine strictness from root config ---
    strict_from_root: Any = parsed_cfg.get("strict_config")
    if strict is None and isinstance(strict_from_root, bool):
        root_strict = strict_from_root
    strict_config: bool = root_strict

    # --- Validate root-level keys ---
    ROOT_SCHEMA = schema_from_typeddict(RootConfigInput)
    prewarn_root: set[str] = set()
    ok, found = _warn_keys_once(
        strict_config, "dry-run", DRYRUN_KEYS, parsed_cfg, "at top-level", DRYRUN_MSG
    )
    valid &= ok
    prewarn_root |= found
    valid &= _check_schema_conformance(
        strict_config, parsed_cfg, ROOT_SCHEMA, "at top-level", prewarn_root
    )

    # --- Validate builds structure ---
    builds_raw: Any = parsed_cfg.get("builds", [])
    if not isinstance(builds_raw, list):
        log("error", "`builds` must be a list")
        return False
    if not builds_raw:
        log("warning", "No builds defined; continuing with empty configuration")
        return valid

    builds = cast_hint(list[Any], builds_raw)
    BUILD_SCHEMA = schema_from_typeddict(BuildConfigInput)
    for i, b in enumerate(builds):
        if not isinstance(b, dict):
            log("error", f"Build #{i} is not a dict")
            valid = False
            continue
        b = cast_hint(dict[str, Any], b)

        # inherit root strictness unless overridden below
        strict_config = root_strict
        strict_from_build: Any = b.get("strict_config")
        if strict is None and isinstance(strict_from_build, bool):
            strict_config = strict_from_build

        prewarn_build: set[str] = set()
        ok, found = _warn_keys_once(
            strict_config, "dry-run", DRYRUN_KEYS, b, f"in build #{i}", DRYRUN_MSG
        )
        valid &= ok
        prewarn_build |= found
        ok, found = _warn_keys_once(
            strict_config,
            "root-only",
            ROOT_ONLY_KEYS,
            b,
            f"in build #{i}",
            ROOT_ONLY_MSG,
        )
        valid &= ok
        prewarn_build |= found
        valid &= _check_schema_conformance(
            strict_config, b, BUILD_SCHEMA, f"in build #{i}", prewarn_build
        )

    return valid
