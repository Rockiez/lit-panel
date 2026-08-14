#!/usr/bin/env python3
"""兼容入口：加载随 lit-panel 技能包分发的机械核验实现。"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


_IMPLEMENTATION = (
    Path(__file__).resolve().parent.parent
    / "skills"
    / "lit-panel"
    / "scripts"
    / "verify-quotes.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "_lit_panel_verify_quotes_impl", _IMPLEMENTATION
)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError(f"无法加载 lit-panel 引证核验实现: {_IMPLEMENTATION}")

_MODULE = importlib.util.module_from_spec(_SPEC)
# dataclasses 会按类的 __module__ 回查 sys.modules；执行前必须注册模块。
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)

# 保持原脚本可导入 API 兼容，测试和现有调用方无需迁移。
globals().update(
    {
        name: value
        for name, value in vars(_MODULE).items()
        if not name.startswith("__")
    }
)


if __name__ == "__main__":
    raise SystemExit(_MODULE.main())
