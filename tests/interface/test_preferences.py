import os
import sys
import pytest

import sanpy
from sanpy.interface.sanpy_app import SanPyWindow
from sanpy.interface import preferences

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

def _test_preferences(qtbot):
    spw = SanPyWindow()
    p = preferences(spw)
    assert p is not None