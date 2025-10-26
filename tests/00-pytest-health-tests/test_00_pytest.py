# tests/test_00_pytest.py
# These tests are here whenever we need to troubleshoot
#   that pytest itself works with the current config. The
#   tests here should always pass and do not invoke our
#   module itself.


# this test does not use runtime_env
def test_pytest_runs() -> None:
    """Minimal test to confirm pytest is functioning."""
    # --- verify ---
    assert True
