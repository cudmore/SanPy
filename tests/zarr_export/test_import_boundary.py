import subprocess
import sys


def test_ordinary_sanpy_import_does_not_import_export_dependencies():
    command = [
        sys.executable,
        "-c",
        "import sanpy,sys; assert 'zarr' not in sys.modules; assert 'jsonschema' not in sys.modules",
    ]
    subprocess.run(command, check=True)
