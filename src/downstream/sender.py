"""sender"""

import base64
from typing import NamedTuple
from logger.send_log import get_loger
from queues import queues
from storage.sqlite import get_db

_MAX_FILE_SIZE = 30 * 1024 * 1024  # 30MB
_FILE_TYPES = {
    "doc": "doc", "docx": "doc",
    "xls": "xls", "xlsx": "xls",
    "ppt": "ppt", "pptx": "ppt",
    "pdf": "pdf",
    "mp4": "mp4",
}  # 其余扩展名 → stream


class SubmitResult(NamedTuple):
    http_status: int
    code: int
    message: str
    data: dict | None


def submit_text(program, target, content) -> SubmitResult:
    """/send/text 业务：校验、入 Q2、记录 send.log。"""
    p = get_db().get_program(program)
    if p is None:
        res = SubmitResult(400, 4001, f"程序未注册: {program}", None)
        # 程序未注册：程序id 与调用方 base_url 均留空
        get_loger().write(None, program, target, "text", None, res.http_status, res.code)
        return res

    queues.Q2.put({"kind": "text", "program": p["name"], "program_id": p["id"],
                   "target": target, "content": content})

    res = SubmitResult(200, 0, "ok", {"queued": True})

    get_loger().write(p["id"], p["name"], target, "text", p["base_url"],
                      res.http_status, res.code)
    return res


def submit_file(program, target, file_name, content_base64, duration_ms) -> SubmitResult:
    """/send/file 业务：全部校验在入队前完成。"""
    p = get_db().get_program(program)
    if p is None:
        res = SubmitResult(400, 4001, f"程序未注册: {program}", None)
        get_loger().write(None, program, target, "file", None, res.http_status, res.code)
        return res

    ext = file_name.rsplit(".", 1)[1].lower() if "." in file_name else ""
    if not ext:
        return _file_fail(p, target, 4003, "文件名不合法（含缺扩展名）")

    try:
        data = base64.b64decode(content_base64, validate=True)
    except Exception:
        return _file_fail(p, target, 4004, "不合法 base64")

    if not data:
        return _file_fail(p, target, 4004, "不合法 base64")

    if len(data) > _MAX_FILE_SIZE:
        return _file_fail(p, target, 4005, "文件超过 30MB")

    file_type = _FILE_TYPES.get(ext, "stream")
    if file_type == "mp4":
        if duration_ms is None:
            return _file_fail(p, target, 4006, "时长缺失")
        if duration_ms <= 0:
            return _file_fail(p, target, 4007, "duration_ms 必须大于 0")
    else:
        duration_ms = None  # 非 mp4 忽略时长

    queues.Q2.put({"kind": "file", "program": p["name"], "program_id": p["id"],
                   "target": target, "file_name": file_name, "data": data,
                   "file_type": file_type, "duration_ms": duration_ms})

    res = SubmitResult(200, 0, "ok", {"queued": True})

    get_loger().write(p["id"], p["name"], target, "file", p["base_url"],
                      res.http_status, res.code)
    return res


def _file_fail(p, target, code, message) -> SubmitResult:
    res = SubmitResult(400, code, message, None)
    get_loger().write(p["id"], p["name"], target, "file", p["base_url"],
                      res.http_status, res.code)
    return res
