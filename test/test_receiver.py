"""receiver 模块测试。"""

import json
from types import SimpleNamespace

import pytest

from feishu import receiver
from queues import queues


def _fake_event(event_id, chat_type, message_type, content, open_id="ou_u1"):
    """按 SDK 事件对象形状伪造 P2ImMessageReceiveV1。"""
    return SimpleNamespace(
        header=SimpleNamespace(event_id=event_id),
        event=SimpleNamespace(
            message=SimpleNamespace(chat_type=chat_type,
                                    message_type=message_type, content=content),
            sender=SimpleNamespace(sender_id=SimpleNamespace(open_id=open_id)),
        ),
    )


@pytest.fixture(autouse=True)
def _fresh_receiver(tmp_path, monkeypatch):
    """事件去重集合复位、feishu.log 指向 tmp_path、Q1 清空。"""
    monkeypatch.setattr(receiver, "_event_ids", set())
    monkeypatch.setattr("logger.feishu_log.LOG_DIR", str(tmp_path))
    monkeypatch.setattr("logger.feishu_log._feishu_log", None)
    while queues.Q1.qsize():
        queues.Q1.get()
    yield
    while queues.Q1.qsize():
        queues.Q1.get()


def _read(path):
    with open(path, encoding="utf-8") as f:
        return [line.rstrip("\n") for line in f if line]


def test_p2p_text_enqueued(tmp_path):
    content = json.dumps({"text": "基金 查询 000001"})
    receiver._on_message(_fake_event("e1", "p2p", "text", content, "ou_sender"))

    assert queues.Q1.qsize() == 1
    assert queues.Q1.get() == {"sender": "ou_sender", "raw": "基金 查询 000001"}

    cols = _read(tmp_path / "feishu.log")[0].split("\t")
    assert len(cols) == 2
    assert cols[1] == "ou_sender"


def test_dedup_same_event_id(tmp_path):
    content = json.dumps({"text": "hi"})
    event = _fake_event("e2", "p2p", "text", content)

    receiver._on_message(event)
    receiver._on_message(event)  # 同一 event_id 重推

    assert queues.Q1.qsize() == 1  # 去重生效，只入队一条


def test_group_chat_ignored():
    content = json.dumps({"text": "hi"})
    receiver._on_message(_fake_event("e3", "group", "text", content))
    assert queues.Q1.qsize() == 0


def test_non_text_ignored():
    content = json.dumps({"image_key": "k"})
    receiver._on_message(_fake_event("e4", "p2p", "image", content))
    assert queues.Q1.qsize() == 0


def test_bad_content_silent(tmp_path):
    # content 非法 JSON：异常静默，Q1 不入队、不抛出
    receiver._on_message(_fake_event("e5", "p2p", "text", "{not-json"))
    assert queues.Q1.qsize() == 0
