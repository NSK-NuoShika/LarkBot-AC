"""storage 模块测试。

Database 直接使用模块级 DB_PATH，测试用 monkeypatch 把它指向 tmp_path 下的
临时库文件，避免触碰项目根目录的 data/。
"""

import sqlite3
import time

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
    _, _, overwritten = db.register_program("基金", "http://x", "净值", "/nav")
    assert overwritten is True
    assert _count(db, "command") == 2


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
