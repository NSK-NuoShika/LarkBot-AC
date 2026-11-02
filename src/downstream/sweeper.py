"""sweeper"""

import threading
import time
from config.settings import get_settings
from logger.registry_log import get_loger
from storage.sqlite import get_db


class Sweeper:
    def __init__(self, interval=None, timeout=None):
        if interval is None or timeout is None:
            s = get_settings()
            self._interval = s.sweep_interval if interval is None else interval
            self._timeout = s.heartbeat_timeout if timeout is None else timeout
        else:
            self._interval = interval
            self._timeout = timeout

    def start(self):
        threading.Thread(target=self.run, daemon=True).start()

    def run(self):
        while True:
            time.sleep(self._interval)
            try:
                self.sweep_once()
            except Exception:
                pass  # 静默忽略

    def sweep_once(self):
        """删除超时程序。"""
        deadline = int(time.time()) - self._timeout
        for d in get_db().sweep_expired(deadline):
            get_loger().write_dead(d["id"], d["name"], d["base_url"], d["command_count"])
