"""feishu.log"""

import os
from logger import LOG_DIR, now_iso, tsv

LOG_NAME = "feishu.log"


class FeishuLog:
    def __init__(self):
        os.makedirs(LOG_DIR, exist_ok=True)
        self._fh = open(os.path.join(LOG_DIR, LOG_NAME), "a", encoding="utf-8", buffering=1)

    def write_send(self, program_name, url, target, http_status, biz_code) -> None:
        try:
            self._fh.write(tsv(now_iso(), program_name, url, target, http_status, biz_code) + "\n")
        except Exception:
            pass  # 日志失败不影响主流程

    def write_receive(self, user_id) -> None:
        try:
            self._fh.write(tsv(now_iso(), user_id) + "\n")
        except Exception:
            pass  # 日志失败不影响主流程


_feishu_log: FeishuLog | None = None


def get_loger():
    """模块级实例 feishu_log。"""
    global _feishu_log

    if _feishu_log is None:
        _feishu_log = FeishuLog()

    return _feishu_log
