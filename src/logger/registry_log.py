"""registry.log（注册流水）写手。"""

import os
from logger import LOG_DIR, now_iso, tsv

LOG_NAME = "registry.log"


class RegistryLog:
    def __init__(self):
        os.makedirs(LOG_DIR, exist_ok=True)
        self._fh = open(os.path.join(LOG_DIR, LOG_NAME), "a", encoding="utf-8", buffering=1)

    def write_registry(self, program_id, program_name, base_url, command_id, cmd) -> None:
        try:
            self._fh.write(tsv(now_iso(), "register", program_id, program_name, base_url,
                               command_id, cmd) + "\n")
        except Exception:
            pass  # 日志失败不影响主流程

    def write_dead(self, program_id, program_name, base_url, command_count) -> None:
        """dead 行"""
        try:
            self._fh.write(tsv(now_iso(), "dead", program_id, program_name, base_url,
                               command_count) + "\n")
        except Exception:
            pass  # 日志失败不影响主流程


_registry_log: RegistryLog | None = None


def get_loger():
    """模块级实例 registry_log。"""
    global _registry_log

    if _registry_log is None:
        _registry_log = RegistryLog()

    return _registry_log
