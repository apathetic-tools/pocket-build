# tests/utils/check.py
import sys

import pocket_build as pkg
import pocket_build.logs as mod_logs
from tests.utils import TEST_TRACE


TEST_TRACE(
    "logger_origin",
    f"pkg_get_logger_id={id(pkg.get_logger)}",
    f"logs_get_logger_id={id(mod_logs.get_logger)}",
    f"pkg_get_logger is logs_get_logger? {pkg.get_logger is mod_logs.get_logger}",
)

TEST_TRACE(
    "module_ids",
    f"pkg_logs_module={id(mod_logs)} path={getattr(mod_logs, '__file__', None)}",
    f"sys_modules[pocket_build.logs]={id(sys.modules.get('pocket_build.logs'))}",
)
