# src/pocket_build/utils_schema.py


from dataclasses import dataclass
from difflib import get_close_matches
from typing import Any, TypedDict, cast, get_args, get_origin

from .constants import DEFAULT_HINT_CUTOFF
from .utils import fnmatchcase_portable, plural
from .utils_types import cast_hint, safe_isinstance, schema_from_typeddict


# --- types ----------------------------------------------------------


class _SchErrAggEntry(TypedDict):
    msg: str
    contexts: list[str]


"""
severity, tag

Aggregator structure example:
{
  "strict_warnings": {
      "dry-run": {"msg": DRYRUN_MSG, "contexts": ["in build #0", "in build #2"]},
      ...
  },
  "warnings": { ... }
}
"""
SchemaErrorAggregator = dict[str, dict[str, dict[str, _SchErrAggEntry]]]


# --- dataclasses ------------------------------------------------------


@dataclass
class ValidationSummary:
    valid: bool
    errors: list[str]
    strict_warnings: list[str]
    warnings: list[str]
    strict: bool  # strictness somewhere in our config?


# --- constants ------------------------------------------------------

AGG_STRICT_WARN = "strict_warnings"
AGG_WARN = "warnings"

# --- helpers --------------------------------------------------------


def collect_msg(
    msg: str,
    *,
    strict: bool,
    summary: ValidationSummary,  # modified in function, not returned
    is_error: bool = False,
) -> None:
    """Route a message to the appropriate bucket.
    Errors are always fatal.
    Warnings may escalate to strict_warnings in strict mode.
    """
    if is_error:
        summary.errors.append(msg)
    elif strict:
        summary.strict_warnings.append(msg)
    else:
        summary.warnings.append(msg)


def flush_schema_aggregators(
    *,
    summary: ValidationSummary,
    agg: SchemaErrorAggregator,
) -> None:
    def _clean_context(ctx: str) -> str:
        """Normalize context strings by removing leading 'in' or 'on'."""
        ctx = ctx.strip()
        for prefix in ("in ", "on "):
            if ctx.lower().startswith(prefix):
                return ctx[len(prefix) :].strip()
        return ctx

    def _flush_one(
        bucket: dict[str, dict[str, Any]],
        *,
        strict: bool,
    ) -> None:
        for tag, entry in bucket.items():
            msg_tmpl = entry["msg"]
            contexts = [_clean_context(c) for c in entry["contexts"]]
            joined_ctx = ", ".join(contexts)
            rendered = msg_tmpl.format(keys=tag, ctx=f"in {joined_ctx}")
            collect_msg(rendered, strict=strict, summary=summary)
        bucket.clear()

    strict_bucket = agg.get(AGG_STRICT_WARN, {})
    warn_bucket = agg.get(AGG_WARN, {})

    if strict_bucket:
        summary.valid = False
        _flush_one(strict_bucket, strict=True)
    if warn_bucket:
        _flush_one(warn_bucket, strict=False)


# ---------------------------------------------------------------------------
# granular schema validator helpers (private and testable)
# ---------------------------------------------------------------------------


def _get_example_for_field(
    field_path: str,
    field_examples: dict[str, str] | None = None,
) -> str | None:
    """Get example for field if available in field_examples.

    Args:
        field_path: The full field path
            (e.g. "root.builds.*.include" or "root.watch_interval")
        field_examples: Optional dict mapping field patterns to example values.
        If None, returns None (no examples available).
    """
    if field_examples is None:
        return None

    # First, try exact match (O(1) lookup)
    if field_path in field_examples:
        return field_examples[field_path]

    # Then try wildcard matches
    for pattern, example in field_examples.items():
        if "*" in pattern and fnmatchcase_portable(field_path, pattern):
            return example

    return None


def _infer_type_label(
    expected_type: Any,
) -> str:
    """Return a readable label for logging (e.g. 'list[str]', 'BuildConfig')."""
    try:
        origin = get_origin(expected_type)
        args = get_args(expected_type)
        if origin is list and args:
            return f"list[{getattr(args[0], '__name__', repr(args[0]))}]"
        if isinstance(expected_type, type):
            return expected_type.__name__
        return str(expected_type)
    except Exception:  # noqa: BLE001
        return repr(expected_type)


def _validate_scalar_value(
    context: str,
    key: str,
    val: Any,
    expected_type: Any,
    *,
    strict: bool,
    summary: ValidationSummary,  # modified in function, not returned
    field_path: str,
    field_examples: dict[str, str] | None = None,
) -> bool:
    """Validate a single non-container value against its expected type."""
    try:
        if safe_isinstance(val, expected_type):  # self-ref guard
            return True
    except Exception:  # noqa: BLE001
        # Defensive fallback — e.g. weird typing generics
        fallback_type = (
            expected_type if isinstance(expected_type, type) else type(expected_type)
        )
        if isinstance(val, fallback_type):
            return True

    exp_label = _infer_type_label(expected_type)
    example = _get_example_for_field(field_path, field_examples)
    exmsg = ""
    if example:
        exmsg = f" (e.g. {example})"

    msg = (
        f"{context}: key `{key}` expected {exp_label}{exmsg}, got {type(val).__name__}"
    )
    collect_msg(msg, summary=summary, strict=strict, is_error=True)
    return False


def _validate_list_value(
    context: str,
    key: str,
    val: Any,
    subtype: Any,
    *,
    strict: bool,
    summary: ValidationSummary,  # modified in function, not returned
    prewarn: set[str],
    field_path: str,
    field_examples: dict[str, str] | None = None,
) -> bool:
    """Validate a homogeneous list value, delegating to scalar/TypedDict validators."""
    if not isinstance(val, list):
        exp_label = f"list[{_infer_type_label(subtype)}]"
        example = _get_example_for_field(field_path, field_examples)
        exmsg = ""
        if example:
            exmsg = f" (e.g. {example})"
        msg = (
            f"{context}: key `{key}` expected {exp_label}{exmsg},"
            f" got {type(val).__name__}"
        )
        collect_msg(
            msg,
            strict=strict,
            summary=summary,
            is_error=True,
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
                collect_msg(
                    f"{context}: key `{key}` #{i + 1} expected an "
                    " object with named keys for "
                    f"{subtype.__name__}, got {type(item).__name__}",
                    strict=strict,
                    summary=summary,
                    is_error=True,
                )
                valid = False
                continue
            valid &= _validate_typed_dict(
                f"{context}.{key}[{i}]",
                item,
                subtype,
                strict=strict,
                summary=summary,
                prewarn=prewarn,
                field_path=f"{field_path}[{i}]",
                field_examples=field_examples,
            )
        else:
            valid &= _validate_scalar_value(
                context,
                f"{key}[{i}]",
                item,
                subtype,
                strict=strict,
                summary=summary,
                field_path=f"{field_path}[{i}]",
                field_examples=field_examples,
            )
    return valid


def _dict_unknown_keys(
    context: str,
    val: Any,
    schema: dict[str, Any],
    *,
    strict: bool,
    summary: ValidationSummary,  # modified in function, not returned
    prewarn: set[str],
) -> bool:
    # --- Unknown keys ---
    val_dict = cast("dict[str, Any]", val)
    unknown: list[str] = [k for k in val_dict if k not in schema and k not in prewarn]
    if unknown:
        joined = ", ".join(f"`{u}`" for u in unknown)

        location = context
        if "in top-level configuration." in location:
            location = "in " + location.split("in top-level configuration.")[-1]

        msg = f"Unknown key{plural(unknown)} {joined} {location}."

        hints: list[str] = []
        for k in unknown:
            close = get_close_matches(k, schema.keys(), n=1, cutoff=DEFAULT_HINT_CUTOFF)
            if close:
                hints.append(f"'{k}' → '{close[0]}'")
        if hints:
            msg += "\nHint: did you mean " + ", ".join(hints) + "?"

        collect_msg(msg.strip(), strict=strict, summary=summary)
        if strict:
            return False

    return True


def _dict_fields(
    context: str,
    val: Any,
    schema: dict[str, Any],
    *,
    strict: bool,
    summary: ValidationSummary,  # modified in function, not returned
    prewarn: set[str],
    ignore_keys: set[str],
    field_path: str,
    field_examples: dict[str, str] | None = None,
) -> bool:
    valid = True

    for field, expected_type in schema.items():
        if field not in val or field in prewarn or field in ignore_keys:
            # Optional or missing field → not a failure
            continue

        inner_val = val[field]
        origin = get_origin(expected_type)
        args = get_args(expected_type)
        exp_label = _infer_type_label(expected_type)
        current_field_path = f"{field_path}.{field}" if field_path else field

        if origin is list:
            subtype = args[0] if args else Any
            valid &= _validate_list_value(
                context,
                field,
                inner_val,
                subtype,
                strict=strict,
                summary=summary,
                prewarn=prewarn,
                field_path=current_field_path,
                field_examples=field_examples,
            )
        elif (
            isinstance(expected_type, type)
            and hasattr(expected_type, "__annotations__")
            and hasattr(expected_type, "__total__")
        ):
            # we don't pass ignore_keys down because
            # we don't recursively ignore these keys
            # and they have no depth syntax. Instead you
            # need to ignore the current level, then take ownership
            # and only validate what you want manually. calling validation
            # on anything that you aren't ignoring downstream.
            # rare case that is a lot of work, but keeps the rest
            # simple for now.
            if "in top-level configuration." in context:
                location = field
            else:
                location = f"{context}.{field}"
            valid &= _validate_typed_dict(
                location,
                inner_val,
                expected_type,
                strict=strict,
                summary=summary,
                prewarn=prewarn,
                field_path=current_field_path,
                field_examples=field_examples,
            )
        else:
            val_scalar = _validate_scalar_value(
                context,
                field,
                inner_val,
                expected_type,
                strict=strict,
                summary=summary,
                field_path=current_field_path,
                field_examples=field_examples,
            )
            if not val_scalar:
                collect_msg(
                    f"{context}: key `{field}` expected {exp_label}, "
                    f"got {type(inner_val).__name__}",
                    strict=strict,
                    summary=summary,
                    is_error=True,
                )
                valid = False

    return valid


def _validate_typed_dict(
    context: str,
    val: Any,
    typedict_cls: type[Any],
    *,
    strict: bool,
    summary: ValidationSummary,  # modified in function, not returned
    prewarn: set[str],
    ignore_keys: set[str] | None = None,
    field_path: str = "",
    field_examples: dict[str, str] | None = None,
) -> bool:
    """Validate a dict against a TypedDict schema recursively.

    - Return False if val is not a dict
    - Recurse into its fields using _validate_scalar_value or _validate_list_value
    - Warn about unknown keys under strict=True
    """
    if ignore_keys is None:
        ignore_keys = set()

    if not isinstance(val, dict):
        collect_msg(
            f"{context}: expected an object with named keys for"
            f" {typedict_cls.__name__}, got {type(val).__name__}",
            strict=strict,
            summary=summary,
            is_error=True,
        )
        return False

    if not hasattr(typedict_cls, "__annotations__"):
        xmsg = (
            "Internal schema invariant violated: "
            f"{typedict_cls!r} has no __annotations__."
        )
        raise AssertionError(xmsg)

    schema = schema_from_typeddict(typedict_cls)
    valid = True

    # --- walk through all the fields recursively ---
    if not _dict_fields(
        context,
        val,
        schema,
        strict=strict,
        summary=summary,
        prewarn=prewarn,
        ignore_keys=ignore_keys,
        field_path=field_path,
        field_examples=field_examples,
    ):
        valid = False

    # --- Unknown keys ---
    if not _dict_unknown_keys(
        context,
        val,
        schema,
        strict=strict,
        summary=summary,
        prewarn=prewarn,
    ):
        valid = False

    return valid


# ---------------------------------------------------------------------------
# granular schema validator
# ---------------------------------------------------------------------------


# --- warn_keys_once -------------------------------------------


def warn_keys_once(
    tag: str,
    bad_keys: set[str],
    cfg: dict[str, Any],
    context: str,
    msg: str,
    *,
    strict_config: bool,
    summary: ValidationSummary,  # modified in function, not returned
    agg: SchemaErrorAggregator | None,
) -> tuple[bool, set[str]]:
    """Warn once for known bad keys (e.g. dry-run, root-only).

    agg indexes are: severity, tag, msg, context (list[str])

    Returns (valid, found_keys).
    """
    valid = True

    # Normalize keys to lowercase for case-insensitive matching
    bad_keys_lower = {k.lower(): k for k in bad_keys}
    cfg_keys_lower = {k.lower(): k for k in cfg}
    found_lower = bad_keys_lower & cfg_keys_lower.keys()

    if not found_lower:
        return True, set()

    # Recover original-case keys for display
    found = {cfg_keys_lower[k] for k in found_lower}

    if agg is not None:
        # record context for later aggregation
        severity = AGG_STRICT_WARN if strict_config else AGG_WARN
        bucket = cast_hint(dict[str, _SchErrAggEntry], agg.setdefault(severity, {}))

        default_entry: _SchErrAggEntry = {"msg": msg, "contexts": []}
        entry = bucket.setdefault(tag, default_entry)
        entry["contexts"].append(context)
    else:
        # immediate fallback
        collect_msg(
            f"{msg.format(keys=', '.join(sorted(found)), ctx=context)}",
            strict=strict_config,
            summary=summary,
        )

    if strict_config:
        valid = False

    return valid, found


# --- check_schema_conformance --------------------


def check_schema_conformance(
    cfg: dict[str, Any],
    schema: dict[str, Any],
    context: str,
    *,
    strict_config: bool,
    summary: ValidationSummary,  # modified in function, not returned
    prewarn: set[str] | None = None,
    ignore_keys: set[str] | None = None,
    base_path: str = "root",
    field_examples: dict[str, str] | None = None,
) -> bool:
    """Thin wrapper around _validate_typed_dict for root-level schema checks."""
    if prewarn is None:
        prewarn = set()
    if ignore_keys is None:
        ignore_keys = set()

    # Pretend schema is a TypedDict for uniformity
    class _AnonTypedDict(TypedDict):
        pass

    # Attach the schema dynamically to mimic schema_from_typeddict output
    _AnonTypedDict.__annotations__ = schema

    return _validate_typed_dict(
        context,
        cfg,
        _AnonTypedDict,
        strict=strict_config,
        summary=summary,
        prewarn=prewarn,
        ignore_keys=ignore_keys,
        field_path=base_path,
        field_examples=field_examples,
    )
