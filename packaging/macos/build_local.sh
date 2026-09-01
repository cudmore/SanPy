#!/usr/bin/env bash
# Build an unsigned arm64 SanPy.app for local smoke testing.
# Fail fast: no codesign, no notary, no Intel, no workarounds.
set -euo pipefail

cd "$(dirname "$0")"
REPO_ROOT="$(cd ../.. && pwd)"

if [[ "$(uname -m)" != "arm64" ]]; then
  echo "error: packaging/macos is arm64-only (got $(uname -m))" >&2
  exit 1
fi

if ! command -v uv >/dev/null 2>&1; then
  echo "error: uv not found on PATH" >&2
  exit 1
fi

if [[ -x .venv/bin/python ]]; then
  VENV_PYTHON_VERSION="$(.venv/bin/python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
else
  VENV_PYTHON_VERSION=""
fi

if [[ "${VENV_PYTHON_VERSION}" != "3.11" ]]; then
  echo "==> creating .venv with Python 3.11"
  uv venv --clear --python 3.11 .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

python -c "
import platform
import sys
machine = platform.machine()
if machine != 'arm64':
    raise SystemExit(f'error: venv is not arm64 (got {machine})')
if sys.version_info[:2] != (3, 11):
    raise SystemExit(f'error: venv is not Python 3.11 (got {sys.version.split()[0]})')
print(sys.executable)
print(sys.version)
print('machine', machine)
"

echo "==> installing legacy scientific stack, SanPy [gui], and PyInstaller"
uv pip install \
  --overrides legacy-overrides.txt \
  -e "${REPO_ROOT}[gui]" \
  pyinstaller

echo "==> dependency compatibility gate"
uv pip check

echo "==> import gate"
python -c "
from PyQt5 import QtCore
import numpy
import pandas
import scipy
import tables
import skimage
import h5py
import sanpy
if numpy.__version__ != '1.23.5':
    raise SystemExit(f'error: expected numpy 1.23.5 (got {numpy.__version__})')
if pandas.__version__ != '1.5.3':
    raise SystemExit(f'error: expected pandas 1.5.3 (got {pandas.__version__})')
if scipy.__version__ != '1.10.1':
    raise SystemExit(f'error: expected scipy 1.10.1 (got {scipy.__version__})')
print('PyQt5', QtCore.PYQT_VERSION_STR)
print('numpy', numpy.__version__)
print('pandas', pandas.__version__)
print('scipy', scipy.__version__)
print('tables', tables.__version__)
print('skimage', skimage.__version__)
print('h5py', h5py.__version__)
print('sanpy', sanpy.__version__)
"

echo "==> pyinstaller"
pyinstaller --noconfirm --clean --distpath dist --workpath build sanpy.spec

APP="dist/SanPy.app"
if [[ ! -d "${APP}" ]]; then
  echo "error: expected ${APP}" >&2
  exit 1
fi

echo "unsigned app: ${PWD}/${APP}"
echo "smoke test:   open ${PWD}/${APP}"
