"""heartbeat 模块测试。"""

from downstream.heartbeat import beat
from downstream.register import register


def test_beat_registered(tmp_env):
    register("基金", "http://x", "查询", "/q")
    assert beat("基金") is True


def test_beat_unknown(tmp_env):
    assert beat("不存在") is False
