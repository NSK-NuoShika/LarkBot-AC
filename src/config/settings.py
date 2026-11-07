"""配置模块：读取 .env 与环境变量，校验必填项。"""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

# .env 路径常量（本文件在 src/config/ 下，上三级为项目根目录）
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ENV_PATH = os.path.join(PROJECT_ROOT, ".env")


@dataclass
class Settings:
    app_id: str
    app_secret: str
    port: int = 8000
    heartbeat_timeout: int = 120
    sweep_interval: int = 30
    dispatch_wait: int = 3


_settings: Settings | None = None


def get_settings() -> Settings:
    """首次调用加载 .env 与环境变量。"""
    global _settings

    if _settings is None:
        load_dotenv(ENV_PATH)


        app_id = os.getenv("LARK_APP_ID", "")
        app_secret = os.getenv("LARK_APP_SECRET", "")

        if not app_id or not app_secret:
            raise RuntimeError("缺少 LARK_APP_ID / LARK_APP_SECRET 配置")

        overrides = {}
        for field in ("port", "heartbeat_timeout", "sweep_interval", "dispatch_wait"):
            raw = os.getenv(field.upper())
            if not raw:
                continue
            try:
                value = int(raw)
                if field == "port":
                    if not 1 <= value <= 65535:
                        raise ValueError
                elif value <= 0:
                    raise ValueError
            except ValueError:
                raise RuntimeError(f"配置项 {field.upper()} 非法值: {raw}")
            overrides[field] = value

        _settings = Settings(app_id=app_id, app_secret=app_secret, **overrides)

    return _settings
