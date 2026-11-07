"""storage 模块测试。

Database 直接使用模块级 DB_PATH，测试用 monkeypatch 把它指向 tmp_path 下的
临时库文件，避免触碰项目根目录的 data/。
"""

import sqlite3
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from storage.sqlite import Database


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setattr("storage.sqlite.DB_PATH", str(tmp_path / "t.db"))
    d = Database()
    d.init()
    return d


def _count(db: Database, table: str) -> int:
    conn = sqlite3.connect(db._path)
    try:
        return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    finally:
        conn.close()


def test_register_first_allocates_id(db):
    pid, cid, overwritten = db.register_program("基金", "http://127.0.0.1:9001", "查询", "/query")
    assert 100000 <= pid <= 999999
    assert 100000 <= cid <= 999999
    assert overwritten is False


def test_register_overwrite_same_cmd(db):
    pid1, cid1, _ = db.register_program("基金", "http://127.0.0.1:9001", "查询", "/query")
    pid2, cid2, overwritten = db.register_program("基金", "http://127.0.0.1:9002", "查询", "/query2")
    assert pid1 == pid2
    assert cid1 == cid2  # 同 cmd 接口id不变，只更新 path
    assert overwritten is True
    assert _count(db, "command") == 1  # 同 cmd 只更新 path，接口行数不增


def test_register_second_cmd_accumulates(db):
    db.register_program("基金", "http://x", "查询", "/q")
    _, cid, overwritten = db.register_program("基金", "http://x", "净值", "/nav")
    assert overwritten is False  # 同程序新增接口不算覆盖
    assert _count(db, "command") == 2

    _, cid2, overwritten2 = db.register_program("基金", "http://x", "净值", "/nav2")
    assert overwritten2 is True  # 程序与接口都相同才算覆盖
    assert cid2 == cid


def test_register_concurrent_same_cmd(db):
    """并发注册同一程序同一接口：全部成功且只落一条记录。"""
    n = 8
    barrier = threading.Barrier(n)

    def call(_):
        barrier.wait()
        return db.register_program("基金", "http://x", "查询", "/q")

    with ThreadPoolExecutor(max_workers=n) as executor:
        results = list(executor.map(call, range(n)))

    pid, cid, _ = results[0]
    assert all((p, c) == (pid, cid) for p, c, _ in results)
    assert _count(db, "program") == 1
    assert _count(db, "command") == 1


def test_register_concurrent_different_cmd(db):
    """并发注册同一程序的不同接口：程序唯一，接口全部落库。"""
    n = 8
    barrier = threading.Barrier(n)

    def call(i):
        barrier.wait()
        return db.register_program("基金", "http://x", f"cmd{i}", f"/p{i}")

    with ThreadPoolExecutor(max_workers=n) as executor:
        results = list(executor.map(call, range(n)))

    assert len({p for p, _, _ in results}) == 1
    assert len({c for _, c, _ in results}) == n
    assert _count(db, "program") == 1
    assert _count(db, "command") == n


def test_sweep_holds_write_lock_between_select_and_delete(db, monkeypatch):
    """清扫在 SELECT 与 DELETE 之间持写锁，心跳不能插入窗口。"""
    db.register_program("基金", "http://x", "查询", "/q")
    conn = sqlite3.connect(db._path)
    try:
        conn.execute("UPDATE program SET heart_time = ?", (int(time.time()) - 10_000,))
        conn.commit()
    finally:
        conn.close()

    deleting = threading.Event()
    release = threading.Event()
    orig_connect = db._connect

    def trace(sql):
        if sql.strip().upper().startswith("DELETE FROM COMMAND"):
            deleting.set()
            release.wait(2)

    def connect():
        c = orig_connect()
        c.set_trace_callback(trace)
        return c

    monkeypatch.setattr(db, "_connect", connect)

    sweep_result = {}

    def run_sweep():
        sweep_result["dead"] = db.sweep_expired(int(time.time()) - 120)

    beat_result = {}
    beat_thread = None
    sweep_thread = threading.Thread(target=run_sweep)
    sweep_thread.start()
    try:
        assert deleting.wait(2)

        def run_beat():
            beat_result["ok"] = db.touch_heartbeat("基金")

        beat_thread = threading.Thread(target=run_beat)
        beat_thread.start()
        time.sleep(0.2)
        assert "ok" not in beat_result  # 心跳被清扫的写锁挡住
    finally:
        release.set()
        sweep_thread.join(2)
        if beat_thread is not None:
            beat_thread.join(2)

    assert beat_result["ok"] is False
    assert sweep_result["dead"]
    assert db.get_program("基金") is None


def test_touch_heartbeat(db):
    db.register_program("基金", "http://x", "查询", "/q")
    assert db.touch_heartbeat("基金") is True
    assert db.touch_heartbeat("不存在") is False


def test_get_program(db):
    db.register_program("基金", "http://x", "查询", "/q")
    p = db.get_program("基金")
    assert p is not None
    assert p["name"] == "基金" and p["base_url"] == "http://x"
    assert isinstance(p["heart_time"], int)
    assert db.get_program("不存在") is None


def test_get_route(db):
    db.register_program("基金", "http://127.0.0.1:9001", "查询", "/query")
    r = db.get_route("基金", "查询")
    assert r is not None
    assert r["base_url"] == "http://127.0.0.1:9001" and r["path"] == "/query"
    assert {"program_id", "program_name", "base_url", "command_id", "cmd", "path"} <= set(r)
    assert db.get_route("基金", "无此接口") is None
    assert db.get_route("无此程序", "查询") is None


def test_sweep_expired(db):
    pid, _, _ = db.register_program("基金", "http://x", "查询", "/q")
    past = int(time.time()) - 10_000
    conn = sqlite3.connect(db._path)
    try:
        conn.execute("UPDATE program SET heart_time = ?", (past,))
        conn.commit()
    finally:
        conn.close()
    dead = db.sweep_expired(int(time.time()) - 120)
    assert len(dead) == 1
    assert dead[0]["id"] == pid and dead[0]["name"] == "基金" and dead[0]["base_url"] == "http://x"
    assert dead[0]["command_count"] == 1  # 含本次删除的接口数
    assert _count(db, "program") == 0
    assert _count(db, "command") == 0  # 级联删除接口


def test_sweep_boundary_inclusive(db):
    pid, _, _ = db.register_program("基金", "http://x", "查询", "/q")
    conn = sqlite3.connect(db._path)
    try:
        conn.execute("UPDATE program SET heart_time = ? WHERE id = ?", (1000, pid))
        conn.commit()
    finally:
        conn.close()
    assert db.sweep_expired(1000) != []  # heart_time == 临界时间（含）也删除
    assert _count(db, "program") == 0
