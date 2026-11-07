"""config 模块测试。"""

import pytest

from config import settings as settings_mod

_ENV_VARS = ("LARK_APP_ID", "LARK_APP_SECRET", "PORT",
             "HEARTBEAT_TIMEOUT", "SWEEP_INTERVAL", "DISPATCH_WAIT")


@pytest.fixture(autouse=True)
def _fresh_settings(monkeypatch, tmp_path):
    """每个用例独立环境：清空缓存、指向不存在的 .env、清除全部配置变量。"""
    monkeypatch.setattr(settings_mod, "_settings", None)
    monkeypatch.setattr(settings_mod, "ENV_PATH", str(tmp_path / "no.env"))
    for name in _ENV_VARS:
        monkeypatch.delenv(name, raising=False)


def _set(monkeypatch, **kw):
    for k, v in kw.items():
        monkeypatch.setenv(k, str(v))


def test_fields_and_types(monkeypatch):
    _set(monkeypatch, LARK_APP_ID="cli_a", LARK_APP_SECRET="sec", PORT="9000",
         HEARTBEAT_TIMEOUT="60", SWEEP_INTERVAL="10", DISPATCH_WAIT="5")
    s = settings_mod.get_settings()
    assert s.app_id == "cli_a" and isinstance(s.app_id, str)
    assert s.app_secret == "sec" and isinstance(s.app_secret, str)
    assert s.port == 9000 and isinstance(s.port, int)
    assert s.heartbeat_timeout == 60 and isinstance(s.heartbeat_timeout, int)
    assert s.sweep_interval == 10 and isinstance(s.sweep_interval, int)
    assert s.dispatch_wait == 5 and isinstance(s.dispatch_wait, int)


def test_defaults(monkeypatch):
    _set(monkeypatch, LARK_APP_ID="cli_a", LARK_APP_SECRET="sec")
    s = settings_mod.get_settings()
    assert (s.port, s.heartbeat_timeout, s.sweep_interval, s.dispatch_wait) \
        == (8000, 120, 30, 3)


def test_missing_credentials_raises(monkeypatch):
    with pytest.raises(RuntimeError):
        settings_mod.get_settings()


def test_missing_app_id_only_raises(monkeypatch):
    _set(monkeypatch, LARK_APP_SECRET="sec")
    with pytest.raises(RuntimeError):
        settings_mod.get_settings()


def test_bad_int_raises_not_silent(monkeypatch):
    _set(monkeypatch, LARK_APP_ID="a", LARK_APP_SECRET="b", PORT="abc")
    with pytest.raises(RuntimeError):
        settings_mod.get_settings()


@pytest.mark.parametrize(
    "name, value",
    [
        ("PORT", "0"),
        ("PORT", "65536"),
        ("HEARTBEAT_TIMEOUT", "0"),
        ("HEARTBEAT_TIMEOUT", "-1"),
        ("SWEEP_INTERVAL", "0"),
        ("SWEEP_INTERVAL", "-1"),
        ("DISPATCH_WAIT", "0"),
        ("DISPATCH_WAIT", "-1"),
    ],
)
def test_out_of_range_raises(monkeypatch, name, value):
    _set(monkeypatch, LARK_APP_ID="a", LARK_APP_SECRET="b", **{name: value})
    with pytest.raises(RuntimeError, match=name):
        settings_mod.get_settings()


@pytest.mark.parametrize(
    "name, value",
    [
        ("PORT", "1"),
        ("PORT", "65535"),
        ("HEARTBEAT_TIMEOUT", "1"),
        ("SWEEP_INTERVAL", "1"),
        ("DISPATCH_WAIT", "1"),
    ],
)
def test_boundary_values_accepted(monkeypatch, name, value):
    _set(monkeypatch, LARK_APP_ID="a", LARK_APP_SECRET="b", **{name: value})
    s = settings_mod.get_settings()
    assert getattr(s, name.lower()) == int(value)


def test_cached_singleton(monkeypatch):
    _set(monkeypatch, LARK_APP_ID="a", LARK_APP_SECRET="b")
    assert settings_mod.get_settings() is settings_mod.get_settings()
