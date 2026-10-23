"""Configure imports for standalone NWB export tests."""

from __future__ import annotations

import sys
from pathlib import Path

NWB_IO_DIRECTORY = Path(__file__).resolve().parents[1]
if str(NWB_IO_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(NWB_IO_DIRECTORY))
