#!/usr/bin/env python3
"""Backward-compatible launcher for the packaged structured quote verifier."""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

TARGET = Path(__file__).resolve().parent.parent / "skills" / "lit-panel" / "scripts" / "verify_quotes.py"
sys.path.insert(0, str(TARGET.parent))
runpy.run_path(str(TARGET), run_name="__main__")
