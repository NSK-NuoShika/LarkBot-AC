"""api 模块测试。"""

import pytest
from fastapi.testclient import TestClient

from downstream.api import app
from queues import queues

_REGISTER = {"program": "基金", "base_url": "http://127.0.0.1:9001",
             "cmd": "查询", "path": "/query"}


@pytest.fixture(autouse=True)
def _clean_q2():
    while queues.Q2.qsize():
        queues.Q2.get()
    yield
    while queues.Q2.qsize():
        queues.Q2.get()


@pytest.fixture()
def client(tmp_env, monkeypatch):
    monkeypatch.setattr("logger.send_log.LOG_DIR", str(tmp_env))
    monkeypatch.setattr("logger.send_log._send_log", None)
    return TestClient(app)


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"code": 0, "message": "ok", "data": None}


def test_register_ok(client):
    r = client.post("/register", json=_REGISTER)
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    assert body["data"]["program_id"] >= 100000


def test_register_overwrite_1001(client):
    client.post("/register", json=_REGISTER)
    r = client.post("/register", json=_REGISTER)
    body = r.json()
    assert body["code"] == 1001
    assert "覆盖" in body["message"]  # 实际文案「注册成功（覆盖）」
    assert body["data"]["program_id"] >= 100000


def test_register_invalid_base_url(client):
    bad = dict(_REGISTER, base_url="ftp://x")
    r = client.post("/register", json=bad)
    assert r.status_code == 400
    body = r.json()
    assert body["code"] == 4007 and body["data"] is None


def test_register_missing_field(client):
    r = client.post("/register", json={"program": "基金"})  # 缺 base_url/cmd/path
    assert r.status_code == 400
    assert r.json()["code"] == 4007  # 422 统一转 400/4007


def test_heartbeat_ok(client):
    client.post("/register", json=_REGISTER)
    r = client.post("/heartbeat", json={"program": "基金"})
    assert r.status_code == 200
    assert r.json()["code"] == 0


def test_heartbeat_unknown(client):
    r = client.post("/heartbeat", json={"program": "没有"})
    assert r.status_code == 404
    body = r.json()
    assert body["code"] == 0
    assert body["message"] == "程序未注册: 没有"


def test_send_text_unregistered(client):
    r = client.post("/send/text", json={"program": "没有", "target": "ou_x", "content": "hi"})
    assert r.status_code == 400
    assert r.json()["code"] == 4001


def test_send_text_ok(client):
    client.post("/register", json=_REGISTER)
    before = queues.Q2.qsize()
    r = client.post("/send/text", json={"program": "基金", "target": "ou_x", "content": "hi"})
    assert r.status_code == 200
    assert r.json()["data"] == {"queued": True}
    assert queues.Q2.qsize() == before + 1
