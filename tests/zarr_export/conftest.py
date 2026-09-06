from pathlib import Path

import pytest


@pytest.fixture
def small_abf() -> Path:
    return Path(__file__).parents[1] / "data" / "2021_07_20_0010.abf"
