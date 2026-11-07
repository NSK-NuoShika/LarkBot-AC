"""feishu sender 模块测试。"""

import json
import queue
import threading
import time
from types import SimpleNamespace

import pytest

from feishu import sender as feishu_sender
from queues import queues


class _Resp:
    def __init__(self, code=0, msg="ok", status=200, data=None):
        self.code = code
        self.msg = msg
        self.raw = SimpleNamespace(status_code=status)
        self.data = SimpleNamespace(**(data or {}))

    def success(self):
        return self.code == 0


class _FakeClient:
    """假 lark 客户端：记录调用，响应可注入；响应位置放 Exception 则抛出。"""

    def __init__(self):
        self.calls = []
        self.message_resp = _Resp()
        self.file_resp = _Resp(data={"file_key": "file_key_x"})
        self.image_resp = _Resp(data={"image_key": "image_key_x"})
        self.im = SimpleNamespace(v1=SimpleNamespace(
            message=SimpleNamespace(create=self._message_create),
            file=SimpleNamespace(create=self._file_create),
            image=SimpleNamespace(create=self._image_create),
        ))

    def _message_create(self, request):
        self.calls.append(("message", request))
        if isinstance(self.message_resp, Exception):
            raise self.message_resp
        return self.message_resp

    def _file_create(self, request):
        self.calls.append(("file", request))
        if isinstance(self.file_resp, Exception):
            raise self.file_resp
        return self.file_resp

    def _image_create(self, request):
        self.calls.append(("image", request))
        if isinstance(self.image_resp, Exception):
            raise self.image_resp
        return self.image_resp


@pytest.fixture()
def tmp_feishu(tmp_path, monkeypatch):
    """feishu.log 指向 tmp_path，封面进程缓存复位。"""
    monkeypatch.setattr("logger.feishu_log.LOG_DIR", str(tmp_path))
    monkeypatch.setattr("logger.feishu_log._feishu_log", None)
    monkeypatch.setattr(feishu_sender, "_cover_key", None)
    return tmp_path


def _read(path):
    with open(path, encoding="utf-8") as f:
        return [line.rstrip("\n") for line in f if line]


def test_send_text_ok(tmp_feishu, monkeypatch):
    fake = _FakeClient()
    monkeypatch.setattr(feishu_sender, "_get_client", lambda: fake)
    task = {"kind": "text", "program": "基金", "program_id": 100000,
            "target": "ou_u1", "content": "你好"}

    feishu_sender._send_text(task)

    kind, request = fake.calls[0]
    assert kind == "message"
    assert request.receive_id_type == "open_id"
    assert request.request_body.msg_type == "text"
    assert json.loads(request.request_body.content) == {"text": "你好"}

    cols = _read(tmp_feishu / "feishu.log")[0].split("\t")
    assert cols[1:] == ["基金", feishu_sender.MESSAGES_URL, "ou_u1", "200", "0"]


def test_send_text_lark_error(tmp_feishu, monkeypatch):
    fake = _FakeClient()
    fake.message_resp = _Resp(code=99991668, msg="denied")
    monkeypatch.setattr(feishu_sender, "_get_client", lambda: fake)

    with pytest.raises(feishu_sender.LarkError) as ei:
        feishu_sender._send_text({"kind": "text", "program": "基金",
                                  "program_id": 1, "target": "ou_u1", "content": "x"})
    assert ei.value.code == 99991668
    # 日志照写（取自假响应），行尾业务码为飞书返回码
    cols = _read(tmp_feishu / "feishu.log")[0].split("\t")
    assert cols[-2:] == ["200", "99991668"]


def test_send_file_stream_two_rows(tmp_feishu, monkeypatch):
    fake = _FakeClient()
    monkeypatch.setattr(feishu_sender, "_get_client", lambda: fake)
    task = {"kind": "file", "program": "基金", "program_id": 100000,
            "target": "ou_u1", "file_name": "报表.xlsx",
            "data": b"excel-bytes", "file_type": "xls", "duration_ms": None}

    feishu_sender._send_file(task)

    kinds = [k for k, _ in fake.calls]
    assert kinds == ["file", "message"]  # file.create 与 message.create 各一次
    file_req = fake.calls[0][1]
    assert file_req.request_body.file_type == "xls"
    assert file_req.request_body.file_name == "报表.xlsx"
    assert file_req.request_body.file.read() == b"excel-bytes"
    msg_req = fake.calls[1][1]
    assert msg_req.request_body.msg_type == "file"
    assert json.loads(msg_req.request_body.content) == {"file_key": "file_key_x"}

    rows = _read(tmp_feishu / "feishu.log")
    assert len(rows) == 2  # 发一个文件记两行（上传+发送）


def test_send_file_non_mp4_duration_ignored(tmp_feishu, monkeypatch):
    fake = _FakeClient()
    monkeypatch.setattr(feishu_sender, "_get_client", lambda: fake)
    task = {"kind": "file", "program": "基金", "program_id": 100000,
            "target": "ou_u1", "file_name": "报表.xlsx",
            "data": b"excel-bytes", "file_type": "xls", "duration_ms": 5000}

    feishu_sender._send_file(task)

    file_req = fake.calls[0][1]
    assert file_req.request_body.duration is None


def test_send_file_mp4_cover(tmp_feishu, monkeypatch):
    fake = _FakeClient()
    monkeypatch.setattr(feishu_sender, "_get_client", lambda: fake)
    task = {"kind": "file", "program": "基金", "program_id": 100000,
            "target": "ou_u1", "file_name": "视频.mp4",
            "data": b"mp4-bytes", "file_type": "mp4", "duration_ms": 5000}

    feishu_sender._send_file(task)

    kinds = [k for k, _ in fake.calls]
    assert kinds == ["file", "image", "message"]  # mp4 首次发送多一次封面上传
    file_req = fake.calls[0][1]
    assert file_req.request_body.duration == 5000
    msg_req = fake.calls[2][1]
    assert msg_req.request_body.msg_type == "media"
    assert json.loads(msg_req.request_body.content) == {
        "file_key": "file_key_x", "image_key": "image_key_x"}


def test_cover_cached(tmp_feishu, monkeypatch):
    fake = _FakeClient()
    monkeypatch.setattr(feishu_sender, "_get_client", lambda: fake)
    task = {"kind": "file", "program": "基金", "program_id": 100000,
            "target": "ou_u1", "file_name": "a.mp4",
            "data": b"v", "file_type": "mp4", "duration_ms": 1}

    feishu_sender._send_file(task)
    feishu_sender._send_file(task)

    kinds = [k for k, _ in fake.calls]
    assert kinds.count("image") == 1  # 第二次发送命中进程内缓存，不再上传封面


def test_loop_silent_and_continues(tmp_feishu, monkeypatch):
    q = queue.Queue()
    q.put({"kind": "text", "program": "a", "program_id": 1, "target": "t", "content": "1"})
    monkeypatch.setattr(queues, "Q2", q)

    fake = _FakeClient()
    fake.message_resp = RuntimeError("boom")  # 第一次调用抛异常
    monkeypatch.setattr(feishu_sender, "_get_client", lambda: fake)

    threading.Thread(target=feishu_sender._loop, daemon=True).start()

    deadline = time.time() + 2
    while time.time() < deadline and len(fake.calls) < 1:
        time.sleep(0.01)
    assert len(fake.calls) == 1  # 第一条已消费且抛异常

    fake.message_resp = _Resp()  # 修复 mock，验证循环未死、继续处理下一条
    q.put({"kind": "text", "program": "a", "program_id": 1, "target": "t", "content": "2"})

    log_path = tmp_feishu / "feishu.log"
    deadline = time.time() + 2
    while time.time() < deadline and not log_path.exists():
        time.sleep(0.01)

    assert len(fake.calls) == 2  # 两条都被消费
    assert q.qsize() == 0
    rows = _read(log_path)
    assert len(rows) == 1  # 第一次调用抛异常无响应可记，第二次成功写入一行
