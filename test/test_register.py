"""register 模块测试。"""

import pytest

from downstream.register import register


def _read(path):
    with open(path, encoding="utf-8") as f:
        return [line.rstrip("\n") for line in f if line]


def test_register_ok(tmp_env):
    r = register("基金", "http://127.0.0.1:9001/", "查询", "/query")
    assert 100000 <= r["program_id"] <= 999999
    assert r["overwritten"] is False
    cols = _read(tmp_env / "registry.log")[0].split("\t")
    assert len(cols) == 7
    assert cols[1] == "register"
    assert cols[2] == str(r["program_id"])
    assert cols[3] == "基金"
    assert cols[4] == "http://127.0.0.1:9001"  # 尾部 / 已去
    assert cols[5] != ""  # 真实接口id
    assert cols[6] == "查询"


def test_register_overwrite(tmp_env):
    r1 = register("基金", "http://a", "查询", "/q")
    r2 = register("基金", "http://b", "查询", "/q2")
    assert r2["overwritten"] is True
    assert r2["program_id"] == r1["program_id"]


def test_register_new_cmd_not_overwrite(tmp_env):
    r1 = register("基金", "http://a", "查询", "/q")
    r2 = register("基金", "http://a", "净值", "/nav")
    assert r2["overwritten"] is False
    assert r2["program_id"] == r1["program_id"]

    r3 = register("基金", "http://a", "净值", "/nav2")
    assert r3["overwritten"] is True
    assert r3["program_id"] == r1["program_id"]


def test_empty_program(tmp_env):
    with pytest.raises(ValueError):
        register("  ", "http://127.0.0.1:9001", "查询", "/query")


def test_bad_base_url(tmp_env):
    with pytest.raises(ValueError):
        register("基金", "ftp://127.0.0.1:9001", "查询", "/query")


def test_empty_cmd(tmp_env):
    with pytest.raises(ValueError):
        register("基金", "http://127.0.0.1:9001", "  ", "/query")


def test_bad_path(tmp_env):
    with pytest.raises(ValueError):
        register("基金", "http://127.0.0.1:9001", "查询", "query")


def test_no_log_on_invalid(tmp_env):
    with pytest.raises(ValueError):
        register("基金", "ftp://x", "查询", "/q")
    assert not (tmp_env / "registry.log").exists()
