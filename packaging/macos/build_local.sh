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

if [[ ! -d .venv ]]; then
  echo "==> creating .venv with Python 3.12"
  uv venv --python 3.12 .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

python -c "
import platform
import sys
machine = platform.machine()
if machine != 'arm64':
    raise SystemExit(f'error: venv is not arm64 (got {machine})')
print(sys.executable)
print(sys.version)
print('machine', machine)
"

echo "==> installing SanPy [gui] and PyInstaller"
uv pip install -e "${REPO_ROOT}[gui]"
uv pip install pyinstaller

echo "==> import gate"
python -c "
from PyQt5 import QtCore
import pandas
import tables
import skimage
import h5py
import sanpy
print('PyQt5', QtCore.PYQT_VERSION_STR)
print('pandas', pandas.__version__)
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
