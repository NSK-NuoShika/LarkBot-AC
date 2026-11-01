"""日志模块"""

import os
from datetime import datetime

# 项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(PROJECT_ROOT, "log")

__all__ = ["tsv", "now_iso", "PROJECT_ROOT", "LOG_DIR"]


def tsv(*fields) -> str:
    """拼行"""
    return "\t".join("" if f is None else str(f) for f in fields)


def now_iso() -> str:
    """本地时区、秒级精度的 ISO8601 时间戳。"""
    return datetime.now().isoformat(timespec="seconds")
