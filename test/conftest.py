"""pytest 配置：将 src/ 加入 sys.path，使测试可以 import 各业务包。"""

import sys
from pathlib import Path

_SRC = str(Path(__file__).resolve().parent.parent / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)
