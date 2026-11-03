"""receiver"""

import json
import threading
import lark_oapi as lark
from config.settings import get_settings
from logger.feishu_log import get_loger
from queues import queues

_event_ids = set()


def start():
    def _run():
        handler = lark.EventDispatcherHandler.builder("", "") \
            .register_p2_im_message_receive_v1(_on_message) \
            .build()
        s = get_settings()
        client = lark.ws.Client(s.app_id, s.app_secret, event_handler=handler,
                                log_level=lark.LogLevel.WARNING)
        client.start()  # 阻塞，重连由 SDK 负责

    threading.Thread(target=_run, daemon=True).start()


def _on_message(data):
    """单聊文本原样放 Q1；去重；异常静默。"""
    try:
        event_id = data.header.event_id
        if event_id in _event_ids:
            return  # 飞书可能重推同一事件
        _event_ids.add(event_id)

        msg = data.event.message
        if msg.chat_type != "p2p" or msg.message_type != "text":
            return  # 非单聊/非文本忽略

        text = json.loads(msg.content).get("text", "")
        open_id = data.event.sender.sender_id.open_id
        get_loger().write_receive(open_id)
        queues.Q1.put({"sender": open_id, "raw": text})
    except Exception:
        pass  # 异常静默
