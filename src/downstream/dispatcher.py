"""dispatcher"""

import threading
import requests
from config.settings import get_settings
from logger.dispatch_log import get_loger
from queues import queues
from storage.sqlite import get_db


def start():
    threading.Thread(target=_loop, daemon=True).start()


def _loop():
    while True:
        item = queues.Q1.get()
        try:
            _handle(item)
        except Exception:
            pass  # 静默忽略，循环不死


def _handle(item):
    parts = item["raw"].split()
    if len(parts) < 2:
        return

    route = get_db().get_route(parts[0], parts[1])

    if route is None:
        raise RuntimeError("未匹配到下游程序路由")

    _dispatch(route, item["sender"], parts[2:])


def _dispatch(route, sender, args):
    url = route["base_url"] + route["path"]
    payload = {"sender": sender, "args": args}
    result = {}

    # 一次性子线程跑 POST
    t = threading.Thread(target=_post, args=(url, payload, result), daemon=True)
    t.start()
    t.join(3 * get_settings().dispatch_wait)

    if 'status' not in result:
        get_loger().write_failed(route["program_id"], route["program_name"],
                                 route["command_id"], route["cmd"], "text", url)
        return
    get_loger().write_dispatch(route["program_id"], route["program_name"],
                               route["command_id"], route["cmd"], "text", url,
                               result["status"], result["biz"])


def _post(url, payload, result):
    try:
        resp = requests.post(url, json=payload, timeout=get_settings().dispatch_wait)
    except requests.RequestException:
        return

    result["status"] = resp.status_code
    try:
        result["biz"] = resp.json().get("code", "")
    except Exception:
        result["biz"] = ""  # biz 取下游响应体 code 字段，取不到留空
