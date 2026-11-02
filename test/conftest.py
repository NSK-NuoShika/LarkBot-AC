"""pytest 配置：将 src/ 加入 sys.path，使测试可以 import 各业务包。"""

import sys
from pathlib import Path

import pytest

_SRC = str(Path(__file__).resolve().parent.parent / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)


@pytest.fixture()
def tmp_env(tmp_path, monkeypatch):
    """数据库与 registry.log 指向 tmp_path，业务单例复位，避免触碰项目 data/ log/。"""
    from storage.sqlite import Database

    monkeypatch.setattr("storage.sqlite.DB_PATH", str(tmp_path / "t.db"))
    monkeypatch.setattr("storage.sqlite._db", None)
    monkeypatch.setattr("logger.registry_log.LOG_DIR", str(tmp_path))
    monkeypatch.setattr("logger.registry_log._registry_log", None)
    Database().init()  # 建表，生产环境由 main.py 启动时执行
    return tmp_path
