# src/pocket_build/constants.py
"""
Central constants used across the project.
"""

RUNTIME_MODES = {
    "standalone",  # single stitched file
    "installed",  # poetry-installed / pip-installed / importable
    "zipapp",  # .pyz bundle
}

# --- env keys ---
DEFAULT_ENV_LOG_LEVEL: str = "LOG_LEVEL"
DEFAULT_ENV_RESPECT_GITIGNORE: str = "RESPECT_GITINGORE"
DEFAULT_ENV_WATCH_INTERVAL: str = "WATCH_INTERVAL"

# --- program defaults ---
DEFAULT_LOG_LEVEL: str = "info"
DEFAULT_WATCH_INTERVAL: float = 1.0  # seconds
DEFAULT_RESPECT_GITIGNORE: bool = True
DEFAULT_HINT_CUTOFF: float = 0.75

# --- config defaults ---
DEFAULT_STRICT_CONFIG: bool = True
DEFAULT_OUT_DIR: str = "dist"
