"""数据库模块"""

import os
import sqlite3
import time
from contextlib import contextmanager

# 数据库路径（本文件在 src/storage/ 下，上三级为项目根目录）
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(_PROJECT_ROOT, "data", "larkbow.db")

# 写锁等待秒数，避免并发写直接报 database is locked
_BUSY_TIMEOUT = 5.0

_INIT_SQL = """
CREATE TABLE IF NOT EXISTS program (
    id         INTEGER PRIMARY KEY,
    name       TEXT UNIQUE NOT NULL,
    base_url   TEXT NOT NULL,
    updated_at INTEGER NOT NULL,
    heart_time INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS command (
    id         INTEGER PRIMARY KEY,
    program_id INTEGER NOT NULL REFERENCES program(id) ON DELETE CASCADE,
    cmd        TEXT NOT NULL,
    path       TEXT NOT NULL,
    UNIQUE(program_id, cmd)
);
"""


class Database:
    def __init__(self):
        self._path = DB_PATH

    @contextmanager
    def _conn(self):
        """每操作独立连接：with 内自动提交/回滚，退出即关闭。"""
        conn = self._connect()
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    @contextmanager
    def _write_conn(self):
        """写事务：BEGIN IMMEDIATE 在读取前取得写锁，保证读改写原子。"""
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _connect(self) -> sqlite3.Connection:
        parent = os.path.dirname(self._path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        conn = sqlite3.connect(self._path, timeout=_BUSY_TIMEOUT)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def init(self) -> None:
        """按 database.md 建两张表。"""
        with self._conn() as conn:
            conn.executescript(_INIT_SQL)

    def register_program(self, name: str, base_url: str, cmd: str, path: str) -> tuple[int, int, bool]:
        """注册/覆盖程序与接口，返回 (program_id, command_id, overwritten)。
        overwritten 仅在程序与接口均已存在时为 True。
        """
        with self._write_conn() as conn:
            now = int(time.time())
            row = conn.execute("SELECT id FROM program WHERE name = ?", (name,)).fetchone()
            program_exists = row is not None
            if not program_exists:
                program_id = conn.execute(
                    "SELECT COALESCE(MAX(id), 99999) + 1 FROM program"
                ).fetchone()[0]
                conn.execute(
                    "INSERT INTO program (id, name, base_url, updated_at, heart_time)"
                    " VALUES (?, ?, ?, ?, ?)",
                    (program_id, name, base_url, now, now),
                )
            else:
                program_id = row[0]
                conn.execute(
                    "UPDATE program SET base_url = ?, updated_at = ?, heart_time = ? WHERE id = ?",
                    (base_url, now, now, program_id),
                )
            crow = conn.execute(
                "SELECT id FROM command WHERE program_id = ? AND cmd = ?",
                (program_id, cmd),
            ).fetchone()
            command_exists = crow is not None
            if not command_exists:
                command_id = conn.execute(
                    "SELECT COALESCE(MAX(id), 99999) + 1 FROM command"
                ).fetchone()[0]
                conn.execute(
                    "INSERT INTO command (id, program_id, cmd, path) VALUES (?, ?, ?, ?)",
                    (command_id, program_id, cmd, path),
                )
            else:
                command_id = crow[0]
                conn.execute("UPDATE command SET path = ? WHERE id = ?", (path, command_id))
            return program_id, command_id, program_exists and command_exists

    def touch_heartbeat(self, name: str) -> bool:
        """刷新程序存活时间。"""
        with self._conn() as conn:
            cur = conn.execute(
                "UPDATE program SET heart_time = ? WHERE name = ?",
                (int(time.time()), name),
            )
            return cur.rowcount > 0

    def get_program(self, name: str) -> dict | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT id, name, base_url, heart_time FROM program WHERE name = ?",
                (name,),
            ).fetchone()
            return dict(row) if row is not None else None

    def get_route(self, program_name: str, cmd: str) -> dict | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT p.id AS program_id, p.name AS program_name, p.base_url AS base_url,"
                "       c.id AS command_id, c.cmd AS cmd, c.path AS path"
                "  FROM program p"
                "  JOIN command c ON c.program_id = p.id"
                " WHERE p.name = ? AND c.cmd = ?",
                (program_name, cmd),
            ).fetchone()
            return dict(row) if row is not None else None

    def sweep_expired(self, seconds: int) -> list[dict]:
        """删除 heart_time 不晚于 seconds（调用方计算临界 Unix 秒，含该时刻）的程序，
        级联删除其接口，返回死程序清单。"""
        with self._write_conn() as conn:
            rows = conn.execute(
                "SELECT id, name, base_url FROM program WHERE heart_time <= ?",
                (seconds,),
            ).fetchall()
            dead = []
            for r in rows:
                d = dict(r)
                d["command_count"] = conn.execute(
                    "SELECT COUNT(*) FROM command WHERE program_id = ?", (d["id"],)
                ).fetchone()[0]
                dead.append(d)
            for d in dead:
                conn.execute("DELETE FROM command WHERE program_id = ?", (d["id"],))
                conn.execute("DELETE FROM program WHERE id = ?", (d["id"],))
            return dead


_db: Database | None = None


def get_db() -> Database:
    """模块级单例。"""
    global _db
    if _db is None:
        _db = Database()
    return _db
