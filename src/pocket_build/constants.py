# src/pocket_build/constants.py
"""
Central constants used across the project.
"""

# --- env keys ---
DEFAULT_ENV_LOG_LEVEL: str = "LOG_LEVEL"
DEFAULT_ENV_RESPECT_GITIGNORE: str = "RESPECT_GITINGORE"
DEFAULT_ENV_WATCH_INTERVAL: str = "WATCH_INTERVAL"

# --- config defaults ---
DEFAULT_STRICT_CONFIG: bool = True
DEFAULT_OUT_DIR: str = "dist"
DEFAULT_LOG_LEVEL: str = "info"
DEFAULT_RESPECT_GITIGNORE: bool = True
DEFAULT_WATCH_INTERVAL: float = 1.0  # seconds
