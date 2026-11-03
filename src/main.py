"""main"""

import sys

import uvicorn

from config.settings import get_settings
from downstream import api, dispatcher
from downstream.sweeper import Sweeper
from feishu import receiver
from feishu import sender as feishu_sender
from storage.sqlite import get_db


def main():
    try:
        s = get_settings()
    except RuntimeError as e:
        print(f"启动失败：{e}")
        sys.exit(1)

    get_db().init()        # 建表
    receiver.start()       # 线程① 收飞书
    feishu_sender.start()  # 线程③ 发飞书
    dispatcher.start()     # 线程② 派发
    Sweeper().start()      # 线程④ 清扫
    uvicorn.run(api.app, host="127.0.0.1", port=s.port, access_log=False,
                log_level="warning")


if __name__ == "__main__":
    main()
