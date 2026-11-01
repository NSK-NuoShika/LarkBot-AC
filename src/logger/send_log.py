"""send.log（发送流水）写手。"""

import os
from logger import LOG_DIR, now_iso, tsv

LOG_NAME = "send.log"

class SendLog:
    def __init__(self):
        os.makedirs(LOG_DIR, exist_ok=True)
        self._fh = open(os.path.join(LOG_DIR, LOG_NAME), "a", encoding="utf-8", buffering=1)

    def write(self, program_id, program_name, user_id, msg_type, url, http_status, biz_status) -> None:
        try:
            self._fh.write(tsv(now_iso(), program_id, program_name, user_id, msg_type,
                               url, http_status, biz_status) + "\n")
        except Exception:
            pass  # 日志失败不影响主流程


_send_log: SendLog | None = None


def get_loger():
    """模块级实例 send_log。"""
    global _send_log

    if _send_log is None:
        _send_log = SendLog()

    return _send_log
