"""Configure imports for focused tests outside the repository test root."""

from __future__ import annotations

import sys
from pathlib import Path

_NWB_SCRIPT_DIR = Path(__file__).resolve().parents[1]
if str(_NWB_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_NWB_SCRIPT_DIR))

