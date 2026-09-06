"""Tests for optional import boundaries around Zarr dependencies."""

import subprocess
import sys


def test_ordinary_sanpy_import_does_not_import_export_dependencies() -> None:
    """Keep ordinary SanPy imports independent of optional export packages."""
    command = [
        sys.executable,
        "-c",
        "import sanpy,sys; assert 'zarr' not in sys.modules; assert 'jsonschema' not in sys.modules",
    ]
    subprocess.run(command, check=True)
