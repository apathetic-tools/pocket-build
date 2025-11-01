# tests/_30_utils_tests/schema/utils.py


from typing import Any, TypedDict


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# --- Fixtures / Sample TypedDicts -------------------------------------------


class MiniBuild(TypedDict):
    include: list[str]
    out: str


class Nested(TypedDict):
    meta: dict[str, Any]
    name: str
