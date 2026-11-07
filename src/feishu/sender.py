"""sender"""

import io
import json
import struct
import threading
import zlib

import lark_oapi as lark
from lark_oapi.api.im.v1 import (
    CreateFileRequestBody,
    CreateImageRequestBody,
    CreateMessageRequestBody,
    CreateMessageRequest,
    CreateFileRequest,
    CreateImageRequest,
)

from config.settings import get_settings
from logger.feishu_log import get_loger
from queues import queues

MESSAGES_URL = "https://open.feishu.cn/open-apis/im/v1/messages"
FILES_URL = "https://open.feishu.cn/open-apis/im/v1/files"


class LarkError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


_client = None
_cover_key = None


def _get_client():
    """lark.Client 模块级单例。"""
    global _client
    if _client is None:
        s = get_settings()
        _client = lark.Client.builder().app_id(s.app_id).app_secret(s.app_secret).build()
    return _client


def start():
    threading.Thread(target=_loop, daemon=True).start()


def _loop():
    while True:
        task = queues.Q2.get()
        try:
            if task["kind"] == "text":
                _send_text(task)
            else:
                _send_file(task)
        except Exception:
            pass  # 静默丢弃任务，循环不死


def _send_text(task):
    body = CreateMessageRequestBody.builder() \
        .receive_id(task["target"]) \
        .msg_type("text") \
        .content(json.dumps({"text": task["content"]})) \
        .build()
    request = CreateMessageRequest.builder() \
        .receive_id_type("open_id") \
        .request_body(body) \
        .build()

    resp = _get_client().im.v1.message.create(request)
    get_loger().write_send(task["program"], MESSAGES_URL, task["target"],
                           resp.raw.status_code, resp.code)
    if not resp.success():
        raise LarkError(resp.code, resp.msg)


def _send_file(task):
    file_key = _upload_file(task)

    if task["file_type"] == "mp4":
        image_key = _cover_image_key()
        content = json.dumps({"file_key": file_key, "image_key": image_key})
        msg_type = "media"
    else:
        content = json.dumps({"file_key": file_key})
        msg_type = "file"

    body = CreateMessageRequestBody.builder() \
        .receive_id(task["target"]) \
        .msg_type(msg_type) \
        .content(content) \
        .build()
    request = CreateMessageRequest.builder() \
        .receive_id_type("open_id") \
        .request_body(body) \
        .build()

    resp = _get_client().im.v1.message.create(request)
    get_loger().write_send(task["program"], MESSAGES_URL, task["target"],
                           resp.raw.status_code, resp.code)
    if not resp.success():
        raise LarkError(resp.code, resp.msg)


def _upload_file(task):
    body = CreateFileRequestBody.builder() \
        .file_type(task["file_type"]) \
        .file_name(task["file_name"]) \
        .file(io.BytesIO(task["data"]))
    if task["file_type"] == "mp4" and task["duration_ms"] is not None:
        body = body.duration(task["duration_ms"])
    request = CreateFileRequest.builder().request_body(body.build()).build()

    resp = _get_client().im.v1.file.create(request)
    get_loger().write_send(task["program"], FILES_URL, task["target"],
                           resp.raw.status_code, resp.code)
    if not resp.success():
        raise LarkError(resp.code, resp.msg)
    return resp.data.file_key


def _cover_image_key():
    """mp4 默认封面 image_key：纯标准库在内存生成纯色 PNG 上传，进程内缓存。"""
    global _cover_key
    if _cover_key is None:
        fp = io.BytesIO(_solid_png(128, 128, (77, 107, 182)))
        request = CreateImageRequest.builder() \
            .request_body(CreateImageRequestBody.builder()
                          .image_type("message").image(fp).build()) \
            .build()

        resp = _get_client().im.v1.image.create(request)
        if not resp.success():
            raise LarkError(resp.code, resp.msg)
        _cover_key = resp.data.image_key
    return _cover_key


def _solid_png(w, h, rgb):
    """纯标准库生成纯色 PNG（8bit truecolor）。"""

    def chunk(tag, payload):
        return struct.pack(">I", len(payload)) + tag + payload \
            + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF)

    row = b"\x00" + bytes(rgb) * w  # 每行前置 filter byte 0
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    idat = zlib.compress(row * h)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")
