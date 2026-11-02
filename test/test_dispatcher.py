"""dispatcher 模块测试。"""

import pytest
import requests

from downstream import dispatcher
from downstream.register import register


class _FakeResp:
    status_code = 200

    def json(self):
        return {"code": 0}


@pytest.fixture(autouse=True)
def _settings_env(monkeypatch):
    """dispatcher 依赖 settings.dispatch_wait，测试环境注入凭证与短超时。"""
    monkeypatch.setenv("LARK_APP_ID", "test")
    monkeypatch.setenv("LARK_APP_SECRET", "test")
    monkeypatch.setenv("DISPATCH_WAIT", "1")
    monkeypatch.setattr("config.settings._settings", None)


@pytest.fixture()
def tmp_dispatch_log(tmp_env, monkeypatch):
    monkeypatch.setattr("logger.dispatch_log.LOG_DIR", str(tmp_env))
    monkeypatch.setattr("logger.dispatch_log._dispatch_log", None)
    return tmp_env


def _read(path):
    with open(path, encoding="utf-8") as f:
        return [line.rstrip("\n") for line in f if line]


def test_handle_ok(tmp_dispatch_log, monkeypatch):
    r = register("基金", "http://127.0.0.1:9001", "查询", "/query")
    captured = {}

    def fake_post(url, json=None, timeout=None):
        captured["url"] = url
        captured["payload"] = json
        return _FakeResp()

    monkeypatch.setattr(dispatcher.requests, "post", fake_post)
    dispatcher._handle({"sender": "ou_u1", "raw": "基金 查询 000001"})

    assert captured["url"] == "http://127.0.0.1:9001/query"
    assert captured["payload"] == {"sender": "ou_u1", "args": ["000001"]}
    cols = _read(tmp_dispatch_log / "dispatch.log")[0].split("\t")
    assert len(cols) == 9
    assert cols[1] == str(r["program_id"])
    assert cols[2] == "基金"
    assert cols[3] != ""  # 接口id
    assert cols[4:] == ["查询", "text", "http://127.0.0.1:9001/query", "200", "0"]


def test_handle_failed_row(tmp_dispatch_log, monkeypatch):
    r = register("基金", "http://127.0.0.1:9001", "查询", "/query")

    def timeout_post(url, json=None, timeout=None):
        raise requests.exceptions.Timeout()

    monkeypatch.setattr(dispatcher.requests, "post", timeout_post)
    dispatcher._handle({"sender": "ou_u1", "raw": "基金 查询"})

    cols = _read(tmp_dispatch_log / "dispatch.log")[0].split("\t")
    assert len(cols) == 8
    assert cols[-1] == "发送失败"
    assert cols[1] == str(r["program_id"])
    assert cols[4:7] == ["查询", "text", "http://127.0.0.1:9001/query"]


def test_route_miss_no_log(tmp_dispatch_log, monkeypatch):
    def no_post(url, json=None, timeout=None):
        raise AssertionError("未命中路由不应调用下游")

    monkeypatch.setattr(dispatcher.requests, "post", no_post)
    with pytest.raises(RuntimeError):  # 未命中路由：raise 交由 _loop 兜底
        dispatcher._handle({"sender": "ou_u1", "raw": "没有 查询"})
    assert not (tmp_dispatch_log / "dispatch.log").exists()


def test_malformed_no_log(tmp_dispatch_log, monkeypatch):
    dispatcher._handle({"sender": "ou_u1", "raw": "只有程序名"})
    assert not (tmp_dispatch_log / "dispatch.log").exists()
