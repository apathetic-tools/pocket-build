# tests/5_core/test_get_metadata.py
"""Verify get_metadata() works in both installed and standalone modes."""

import pocket_build.actions as mod_actions


MIN_VERSION_PARTS = 2
MIN_COMMIT_LENGTH = 4


def test_get_metadata_returns_tuple() -> None:
    """Should return a Metadata tuple with version and commit."""
    # --- execute ---
    metadata = mod_actions.get_metadata()

    # --- verify ---
    assert metadata.version is not None
    assert isinstance(metadata.version, str)
    assert len(metadata.version) > 0

    assert metadata.commit is not None
    assert isinstance(metadata.commit, str)
    assert len(metadata.commit) > 0


def test_get_metadata_version_format() -> None:
    """Should return a version in expected format."""
    # --- execute ---
    metadata = mod_actions.get_metadata()

    # --- verify ---
    # Version should be either "unknown" or match semantic versioning
    if metadata.version != "unknown":
        # Allow formats like: 0.1.0, 1.2.3, 1.0.0-alpha, etc.
        parts = metadata.version.split(".")
        msg = f"Version should have at least major.minor: {metadata.version}"
        assert len(parts) >= MIN_VERSION_PARTS, msg


def test_get_metadata_commit_format() -> None:
    """Should return a commit as short hash or 'unknown'."""
    # --- execute ---
    metadata = mod_actions.get_metadata()

    # --- verify ---
    # Commit should be either "unknown", a hex string, or "unknown (local build)"
    commit = metadata.commit
    if "unknown" not in commit.lower():
        # Should be a valid hex string (short commit hash)
        msg = f"Commit should be hex string or contain 'unknown': {commit}"
        assert all(c in "0123456789abcdef" for c in commit.lower()), msg
        msg2 = f"Commit should be at least {MIN_COMMIT_LENGTH} chars: {commit}"
        assert len(commit) >= MIN_COMMIT_LENGTH, msg2
