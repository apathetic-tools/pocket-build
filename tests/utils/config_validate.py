# tests/utils/config_validate.py

import pocket_build.config_validate as mod_validate


def make_summary(
    *,
    valid: bool = True,
    errors: list[str] | None = None,
    strict_warnings: list[str] | None = None,
    warnings: list[str] | None = None,
    strict: bool = True,
) -> mod_validate.ValidationSummary:
    """Helper to create a clean ValidationSummary."""
    return mod_validate.ValidationSummary(
        valid=valid,
        errors=errors or [],
        strict_warnings=strict_warnings or [],
        warnings=warnings or [],
        strict=strict,
    )
