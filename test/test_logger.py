"""logger 模块测试：四个流水写手的列数、字段顺序、超时行与工具函数。

写手类直接使用各自模块的 LOG_DIR，测试用 monkeypatch 把它指向 tmp_path，
避免触碰项目根目录的真实 log/。
"""

import re

from logger import now_iso, tsv
from logger.dispatch_log import DispatchLog
from logger.feishu_log import FeishuLog
from logger.registry_log import RegistryLog
from logger.send_log import SendLog


def _read(path):
    with open(path, encoding="utf-8") as f:
        return [line.rstrip("\n") for line in f if line]


def test_dispatch_write(tmp_path, monkeypatch):
    monkeypatch.setattr("logger.dispatch_log.LOG_DIR", str(tmp_path))
    log = DispatchLog()
    log.write_dispatch(100000, "基金", 100001, "查询", "text", "http://127.0.0.1:9001/query", 200, 0)
    lines = _read(tmp_path / "dispatch.log")
    assert len(lines) == 1
    cols = lines[0].split("\t")
    assert len(cols) == 9
    assert cols[1:] == ["100000", "基金", "100001", "查询", "text",
                        "http://127.0.0.1:9001/query", "200", "0"]


def test_dispatch_write_failed(tmp_path, monkeypatch):
    monkeypatch.setattr("logger.dispatch_log.LOG_DIR", str(tmp_path))
    log = DispatchLog()
    log.write_failed(100000, "基金", 100001, "查询", "text", "http://127.0.0.1:9001/query")
    cols = _read(tmp_path / "dispatch.log")[0].split("\t")
    assert len(cols) == 8
    assert cols[-1] == "发送失败"
    assert cols[1:6] == ["100000", "基金", "100001", "查询", "text"]


def test_send_write(tmp_path, monkeypatch):
    monkeypatch.setattr("logger.send_log.LOG_DIR", str(tmp_path))
    log = SendLog()
    log.write(100000, "基金", "ou_u1", "text", "http://127.0.0.1:8000/send/text", 200, 0)
    cols = _read(tmp_path / "send.log")[0].split("\t")
    # 计划标注「9 列」为笔误：字段清单（同 log.md）实为 8 列
    assert len(cols) == 8
    assert cols[1:] == ["100000", "基金", "ou_u1", "text",
                        "http://127.0.0.1:8000/send/text", "200", "0"]


def test_feishu_write_send(tmp_path, monkeypatch):
    monkeypatch.setattr("logger.feishu_log.LOG_DIR", str(tmp_path))
    log = FeishuLog()
    log.write_send("基金", "https://open.feishu.cn/open-apis/im/v1/messages", "ou_u1", 200, 0)
    cols = _read(tmp_path / "feishu.log")[0].split("\t")
    assert len(cols) == 6
    assert cols[1:] == ["基金", "https://open.feishu.cn/open-apis/im/v1/messages",
                        "ou_u1", "200", "0"]


def test_feishu_write_receive(tmp_path, monkeypatch):
    monkeypatch.setattr("logger.feishu_log.LOG_DIR", str(tmp_path))
    log = FeishuLog()
    log.write_receive("ou_u1")
    cols = _read(tmp_path / "feishu.log")[0].split("\t")
    assert len(cols) == 2
    assert cols[1] == "ou_u1"


def test_registry_write(tmp_path, monkeypatch):
    monkeypatch.setattr("logger.registry_log.LOG_DIR", str(tmp_path))
    log = RegistryLog()
    log.write_registry(100000, "基金", "http://127.0.0.1:9001", 100001, "查询")
    c1 = _read(tmp_path / "registry.log")[0].split("\t")
    assert len(c1) == 7
    assert c1[1:] == ["register", "100000", "基金", "http://127.0.0.1:9001", "100001", "查询"]


def test_registry_write_dead(tmp_path, monkeypatch):
    monkeypatch.setattr("logger.registry_log.LOG_DIR", str(tmp_path))
    log = RegistryLog()
    log.write_dead(100000, "基金", "http://127.0.0.1:9001", 2)
    c2 = _read(tmp_path / "registry.log")[0].split("\t")
    assert len(c2) == 6
    assert c2[1:5] == ["dead", "100000", "基金", "http://127.0.0.1:9001"]
    assert c2[5] == "2"  # 尾列为删除的接口数


def test_append_mode(tmp_path, monkeypatch):
    monkeypatch.setattr("logger.dispatch_log.LOG_DIR", str(tmp_path))
    log = DispatchLog()
    log.write_dispatch(1, "a", 2, "b", "text", "u", 200, 0)
    log2 = DispatchLog()  # 第二个实例追加，不覆盖
    log2.write_dispatch(3, "c", 4, "d", "text", "u", 404, 1)
    assert len(_read(tmp_path / "dispatch.log")) == 2


def test_tsv_none_is_empty_field():
    assert tsv(None) == ""
    assert tsv("a", None, "b") == "a\t\tb"


def test_now_iso_seconds_format():
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", now_iso())
