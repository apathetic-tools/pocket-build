# src/pocket_build/logs.py

import argparse
import logging
import os
from typing import cast

from .constants import DEFAULT_LOG_LEVEL
from .meta import PROGRAM_ENV, PROGRAM_PACKAGE
from .utils_logs import TEST_TRACE, ApatheticCLILogger
from .utils_types import cast_hint


# --- Our application logger -----------------------------------------------------


class AppLogger(ApatheticCLILogger):
    def determine_log_level(
        self,
        *,
        args: argparse.Namespace | None = None,
        root_log_level: str | None = None,
        build_log_level: str | None = None,
    ) -> str:
        """Resolve log level from CLI → env → root config → default."""
        args_level = getattr(args, "log_level", None)
        if args_level is not None and args_level:
            return cast_hint(str, args_level).upper()

        env_log_level = os.getenv(f"{PROGRAM_ENV}_LOG_LEVEL") or os.getenv("LOG_LEVEL")
        if env_log_level:
            return env_log_level.upper()

        if build_log_level:
            return build_log_level.upper()

        if root_log_level:
            return root_log_level.upper()

        return DEFAULT_LOG_LEVEL.upper()


# --- Convenience utils ---------------------------------------------------------


def get_logger() -> AppLogger:
    """Return the configured app logger."""
    logger = _APP_LOGGER
    TEST_TRACE(
        "get_logger() called",
        f"id={id(logger)}",
        f"name={logger.name}",
        f"level={logger.level_name}",
        f"handlers={[type(h).__name__ for h in logger.handlers]}",
    )
    return logger


# --- Logger initialization ---------------------------------------------------

# Force the logging module to use our subclass globally.
# This must happen *before* any loggers are created.
# logging.setLoggerClass(AppLogger)

# Force registration of TRACE and SILENT levels
AppLogger.extend_logging_module()

# Now this will actually return an AppLogger instance.
_APP_LOGGER = cast("AppLogger", logging.getLogger(PROGRAM_PACKAGE))
