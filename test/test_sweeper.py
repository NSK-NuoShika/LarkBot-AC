"""sweeper 模块测试。"""

import sqlite3
import time

from downstream.register import register
from downstream.sweeper import Sweeper
from storage.sqlite import get_db


def _read(path):
    with open(path, encoding="utf-8") as f:
        return [line.rstrip("\n") for line in f if line]


def test_sweep_once(tmp_env):
    register("基金", "http://x", "查询", "/q")
    db = get_db()
    conn = sqlite3.connect(db._path)
    try:
        conn.execute("UPDATE program SET heart_time = ?", (int(time.time()) - 10_000,))
        conn.commit()
    finally:
        conn.close()

    Sweeper(interval=30, timeout=120).sweep_once()  # 不起线程，直接调

    lines = _read(tmp_env / "registry.log")
    assert len(lines) == 2  # register 行 + dead 行
    cols = lines[1].split("\t")
    assert len(cols) == 6
    assert cols[1] == "dead"
    assert cols[3] == "基金"
    assert cols[5] == "1"  # 尾列为删除的接口数
    assert get_db().get_program("基金") is None
