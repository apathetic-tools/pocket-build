# tests/0_independant/test_detect_runtime_mode.py
"""Tests for detect_runtime_mode() function.

The detect_runtime_mode() function checks multiple indicators to
determine how the code is currently running:
1. sys.frozen - PyInstaller/py2exe indicator
2. sys.modules["__main__"].__file__ ending with .pyz - zipapp indicator
3. __STANDALONE__ in globals() - pocket-build's single-file indicator
4. Otherwise: installed package (default)

Note: The zipapp detection works by checking if the file specified by
the utils module's __file__ variable (as an attribute name on __main__)
ends with ".pyz". This is unusual but functional.
"""

import sys
from unittest.mock import MagicMock, patch

import pocket_build.utils as mod_utils


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_detect_runtime_mode_frozen() -> None:
    """Test detection of PyInstaller/py2exe frozen mode.

    When sys.frozen is True, should return "frozen".
    """
    # --- setup ---
    with patch.object(sys, "frozen", True, create=True):
        # --- execute ---
        result = mod_utils.detect_runtime_mode()

    # --- verify ---
    assert result == "frozen"


def test_detect_runtime_mode_zipapp() -> None:
    """Test detection of zipapp mode.

    A zipapp is a zipped Python application, typically ending in .pyz.
    The detection works by checking if the attribute named by utils.__file__
    on the __main__ module ends with ".pyz".

    For example, if utils.__file__ is "/path/to/utils.py", it checks:
    getattr(sys.modules["__main__"], "/path/to/utils.py", "").endswith(".pyz")

    In a real zipapp, __main__ might have an attribute with the zipapp path.
    For testing, we set the __main__ module attribute to a .pyz path.
    """
    # --- setup ---
    # Get the actual __file__ path from utils module
    utils_file = mod_utils.__file__
    assert utils_file is not None

    # Create a mock __main__ module
    mock_main = MagicMock()
    # Set the attribute that matches utils.__file__ to a .pyz path
    setattr(mock_main, utils_file, "/path/to/app.pyz")

    with (
        patch.object(sys, "frozen", False, create=True),
        patch.dict(sys.modules, {"__main__": mock_main}),
    ):
        # --- execute ---
        result = mod_utils.detect_runtime_mode()

    # --- verify ---
    assert result == "zipapp"


def test_detect_runtime_mode_zipapp_complex_path() -> None:
    """Test zipapp detection with complex paths containing multiple separators."""
    # --- setup ---
    utils_file = mod_utils.__file__
    assert utils_file is not None

    mock_main = MagicMock()
    setattr(mock_main, utils_file, "/usr/local/bin/my-app.pyz")

    with (
        patch.object(sys, "frozen", False, create=True),
        patch.dict(sys.modules, {"__main__": mock_main}),
    ):
        # --- execute ---
        result = mod_utils.detect_runtime_mode()

    # --- verify ---
    assert result == "zipapp"


def test_detect_runtime_mode_zipapp_missing_file_attribute() -> None:
    """When __main__ lacks the utils.__file__ attribute, should not match zipapp."""
    # --- setup ---
    # Create a mock __main__ without the utils.__file__ attribute
    mock_main = MagicMock(spec=[])  # spec=[] means no attributes

    with (
        patch.object(sys, "frozen", False, create=True),
        patch.dict(sys.modules, {"__main__": mock_main}),
        patch.dict(
            mod_utils.detect_runtime_mode.__globals__,
            clear=False,
        ) as patched_globals,
    ):
        patched_globals.pop("__STANDALONE__", None)

        # --- execute ---
        result = mod_utils.detect_runtime_mode()

    # --- verify ---
    # Should fall through to installed since no indicators match
    assert result == "installed"


def test_detect_runtime_mode_standalone() -> None:
    """Test detection of standalone mode.

    pocket-build's single-file executable has __STANDALONE__ in globals().
    """
    # --- setup ---
    # Create a context where frozen=False and the zipapp check fails
    utils_file = mod_utils.__file__
    assert utils_file is not None

    mock_main = MagicMock(spec=[])  # No attributes, so zipapp check fails

    with (
        patch.object(sys, "frozen", False, create=True),
        patch.dict(sys.modules, {"__main__": mock_main}),
        patch.dict(
            mod_utils.detect_runtime_mode.__globals__,
            {"__STANDALONE__": True},
            clear=False,
        ),
    ):
        # --- execute ---
        result = mod_utils.detect_runtime_mode()

    # --- verify ---
    assert result == "standalone"


def test_detect_runtime_mode_installed() -> None:
    """Test detection of installed mode (default).

    When no other indicators are present, should return "installed".
    """
    # --- setup ---
    # Create a mock __main__ that doesn't have the zipapp attribute
    mock_main = MagicMock(spec=[])

    with (
        patch.object(sys, "frozen", False, create=True),
        patch.dict(sys.modules, {"__main__": mock_main}),
        patch.dict(
            mod_utils.detect_runtime_mode.__globals__,
            clear=False,
        ) as patched_globals,
    ):
        # Remove __STANDALONE__ if it exists
        patched_globals.pop("__STANDALONE__", None)

        # --- execute ---
        result = mod_utils.detect_runtime_mode()

    # --- verify ---
    assert result == "installed"


def test_detect_runtime_mode_installed_missing_main() -> None:
    """Test installed mode when __main__ is missing from sys.modules.

    This shouldn't normally happen in Python, but we should handle it.
    """
    # --- setup ---
    with (
        patch.object(sys, "frozen", False, create=True),
        patch.dict(sys.modules, {}, clear=False),
    ):  # Remove __main__ if present
        # Ensure __main__ is not in sys.modules for this test
        saved_main = sys.modules.pop("__main__", None)
        try:
            # Ensure __STANDALONE__ is not in globals
            with patch.dict(
                mod_utils.detect_runtime_mode.__globals__,
                clear=False,
            ) as patched_globals:
                patched_globals.pop("__STANDALONE__", None)

                # --- execute ---
                result = mod_utils.detect_runtime_mode()
        finally:
            # Restore __main__ if it was there
            if saved_main is not None:
                sys.modules["__main__"] = saved_main

    # --- verify ---
    assert result == "installed"


def test_detect_runtime_mode_frozen_takes_precedence() -> None:
    """Test that frozen mode takes precedence over other indicators.

    Even if the zipapp or __STANDALONE__ indicators match, if sys.frozen
    is True, it should return "frozen".
    """
    # --- setup ---
    utils_file = mod_utils.__file__
    assert utils_file is not None

    mock_main = MagicMock()
    setattr(mock_main, utils_file, "/path/to/app.pyz")

    with (
        patch.object(sys, "frozen", True, create=True),
        patch.dict(sys.modules, {"__main__": mock_main}),
        patch.dict(
            mod_utils.detect_runtime_mode.__globals__,
            {"__STANDALONE__": True},
            clear=False,
        ),
    ):
        # --- execute ---
        result = mod_utils.detect_runtime_mode()

    # --- verify ---
    assert result == "frozen"


def test_detect_runtime_mode_zipapp_takes_precedence_over_standalone() -> None:
    """Test that zipapp detection takes precedence over standalone.

    If the zipapp check matches, it should return "zipapp" even if
    __STANDALONE__ exists.
    """
    # --- setup ---
    utils_file = mod_utils.__file__
    assert utils_file is not None

    mock_main = MagicMock()
    setattr(mock_main, utils_file, "/path/to/app.pyz")

    with (
        patch.object(sys, "frozen", False, create=True),
        patch.dict(sys.modules, {"__main__": mock_main}),
        patch.dict(
            mod_utils.detect_runtime_mode.__globals__,
            {"__STANDALONE__": True},
            clear=False,
        ),
    ):
        # --- execute ---
        result = mod_utils.detect_runtime_mode()

    # --- verify ---
    assert result == "zipapp"
