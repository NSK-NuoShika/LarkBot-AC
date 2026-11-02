"""sender 模块测试。"""

import base64

import pytest

from downstream.register import register
from downstream.sender import submit_file, submit_text
from queues import queues


@pytest.fixture(autouse=True)
def _clean_q2():
    """Q2 是模块级单例，测试前后清空，互不残留。"""
    while queues.Q2.qsize():
        queues.Q2.get()
    yield
    while queues.Q2.qsize():
        queues.Q2.get()


@pytest.fixture()
def tmp_send_log(tmp_env, monkeypatch):
    monkeypatch.setattr("logger.send_log.LOG_DIR", str(tmp_env))
    monkeypatch.setattr("logger.send_log._send_log", None)
    return tmp_env


def _read(path):
    with open(path, encoding="utf-8") as f:
        return [line.rstrip("\n") for line in f if line]


def test_submit_text_ok(tmp_send_log):
    r = register("基金", "http://127.0.0.1:9001", "查询", "/q")
    res = submit_text("基金", "ou_u1", "今日收益 +2.3%")

    assert res.http_status == 200 and res.code == 0
    assert res.data == {"queued": True}
    assert queues.Q2.qsize() == 1
    task = queues.Q2.get()
    assert task == {"kind": "text", "program": "基金", "program_id": r["program_id"],
                    "target": "ou_u1", "content": "今日收益 +2.3%"}

    cols = _read(tmp_send_log / "send.log")[0].split("\t")
    assert len(cols) == 8
    assert cols[1:] == [str(r["program_id"]), "基金", "ou_u1", "text",
                        "http://127.0.0.1:9001", "200", "0"]


def test_submit_text_unregistered(tmp_send_log):
    res = submit_text("没有", "ou_u1", "hi")

    assert res.http_status == 400 and res.code == 4001
    assert res.message == "程序未注册: 没有"
    assert queues.Q2.qsize() == 0
    cols = _read(tmp_send_log / "send.log")[0].split("\t")
    assert cols[1] == "" and cols[5] == ""  # 程序id 与 url 留空
    assert cols[-2:] == ["400", "4001"]


def test_file_no_ext(tmp_send_log):
    register("基金", "http://x", "查询", "/q")
    res = submit_file("基金", "ou_u1", "报告", base64.b64encode(b"data"), None)
    assert res.code == 4003
    assert queues.Q2.qsize() == 0


def test_file_bad_base64(tmp_send_log):
    register("基金", "http://x", "查询", "/q")
    res = submit_file("基金", "ou_u1", "报告.txt", "!!!not-base64!!!", None)
    assert res.code == 4004
    assert queues.Q2.qsize() == 0


def test_file_empty_base64(tmp_send_log):
    register("基金", "http://x", "查询", "/q")
    res = submit_file("基金", "ou_u1", "报告.txt", base64.b64encode(b""), None)
    assert res.code == 4004
    assert queues.Q2.qsize() == 0


def test_file_too_large(tmp_send_log, monkeypatch):
    register("基金", "http://x", "查询", "/q")
    from downstream import sender
    monkeypatch.setattr(sender, "_MAX_FILE_SIZE", 10)  # 缩小阈值，不必真造 30MB
    res = submit_file("基金", "ou_u1", "报告.txt", base64.b64encode(b"0123456789abcdef"), None)
    assert res.code == 4005
    assert queues.Q2.qsize() == 0


def test_file_mp4_without_duration(tmp_send_log):
    register("基金", "http://x", "查询", "/q")
    res = submit_file("基金", "ou_u1", "视频.mp4", base64.b64encode(b"v"), None)
    assert res.code == 4006
    assert queues.Q2.qsize() == 0


def test_file_ok_xlsx(tmp_send_log):
    r = register("基金", "http://x", "查询", "/q")
    res = submit_file("基金", "ou_u1", "报表.XLSX", base64.b64encode("表格内容".encode("utf-8")), None)

    assert res.http_status == 200 and res.code == 0
    assert queues.Q2.qsize() == 1
    task = queues.Q2.get()
    assert task["data"] == "表格内容".encode("utf-8")  # data 与解码内容一致
    assert task["file_type"] == "xls"  # 扩展名大小写不敏感
    assert task["duration_ms"] is None

    cols = _read(tmp_send_log / "send.log")[0].split("\t")
    assert cols[1:] == [str(r["program_id"]), "基金", "ou_u1", "file", "http://x", "200", "0"]


def test_file_ok_mp4_with_duration(tmp_send_log):
    register("基金", "http://x", "查询", "/q")
    res = submit_file("基金", "ou_u1", "视频.mp4", base64.b64encode(b"v"), 5000)
    assert res.code == 0
    task = queues.Q2.get()
    assert task["file_type"] == "mp4"
    assert task["duration_ms"] == 5000


def test_file_unknown_ext_maps_stream(tmp_send_log):
    register("基金", "http://x", "查询", "/q")
    res = submit_file("基金", "ou_u1", "压缩包.7z", base64.b64encode(b"z"), None)
    assert res.code == 0
    task = queues.Q2.get()
    assert task["file_type"] == "stream"
