"""queues 模块测试。"""

from queues import queues


def test_q1_roundtrip():
    item = {"sender": "ou_u1", "raw": "基金 查询 000001"}
    queues.Q1.put(item)
    assert queues.Q1.qsize() == 1
    assert queues.Q1.get() == item
    assert queues.Q1.qsize() == 0


def test_q2_roundtrip():
    task = {"kind": "text", "program": "基金", "program_id": 100000,
            "target": "ou_u1", "content": "hi"}
    queues.Q2.put(task)
    assert queues.Q2.qsize() == 1
    assert queues.Q2.get() == task
    assert queues.Q2.qsize() == 0


def test_q1_q2_isolated():
    queues.Q2.put({"kind": "text"})
    assert queues.Q1.qsize() == 0  # Q2 放入不影响 Q1
    queues.Q1.put({"raw": "x"})
    assert queues.Q2.qsize() == 1  # Q1 放入不影响 Q2 原有元素
    assert queues.Q1.get() == {"raw": "x"}
    assert queues.Q2.get() == {"kind": "text"}
    assert queues.Q1.qsize() == 0 and queues.Q2.qsize() == 0
