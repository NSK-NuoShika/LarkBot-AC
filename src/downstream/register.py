"""register"""

import re
from logger.registry_log import get_loger
from storage.sqlite import get_db

_BASE_URL_RE = re.compile(r"^https?://\S+$")


def register(program, base_url, cmd, path) -> dict:
    """/register 业务：校验、写库、记录 registry.log。"""
    program = (program or "").strip()
    base_url = (base_url or "").strip()
    cmd = (cmd or "").strip()

    if not program:
        raise ValueError("program 不能为空")
    if not _BASE_URL_RE.match(base_url):
        raise ValueError("base_url 不合法")
    if not cmd:
        raise ValueError("cmd 不能为空")
    if not path.startswith("/"):
        raise ValueError("path 必须以 / 开头")

    base_url = base_url.rstrip("/")
    program_id, command_id, overwritten = get_db().register_program(program, base_url, cmd, path)

    get_loger().write_registry(program_id, program, base_url, command_id, cmd)

    return {"program_id": program_id, "overwritten": overwritten}
