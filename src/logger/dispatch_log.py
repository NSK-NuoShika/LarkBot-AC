"""dispatch.log"""

import os
from logger import LOG_DIR, now_iso, tsv

LOG_NAME = "dispatch.log"


class DispatchLog:
    def __init__(self):
        os.makedirs(LOG_DIR, exist_ok=True)

        # 追加模式、行缓冲
        self._fh = open(os.path.join(LOG_DIR, LOG_NAME), "a", encoding="utf-8", buffering=1)

    def write_dispatch(self, program_id, program_name, command_id, cmd, msg_type, url, http_status, biz_status) -> None:
        try:
            self._fh.write(tsv(now_iso(), program_id, program_name, command_id, cmd,
                               msg_type, url, http_status, biz_status) + "\n")
        except Exception:
            pass  # 日志失败不影响主流程

    def write_timeout(self, program_id, program_name, command_id, cmd, msg_type, url) -> None:
        try:
            self._fh.write(tsv(now_iso(), program_id, program_name, command_id, cmd,
                               msg_type, url, "超时") + "\n")
        except Exception:
            pass  # 日志失败不影响主流程


_dispatch_log: DispatchLog | None = None


def get_loger():
    """模块级实例 dispatch_log"""
    global _dispatch_log

    if _dispatch_log is None:
        _dispatch_log = DispatchLog()
        
    return _dispatch_log
