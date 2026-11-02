"""heartbeat"""

from storage.sqlite import get_db


def beat(program) -> bool:
    """/heartbeat 业务：刷新存活时间。"""
    return get_db().touch_heartbeat(program)
