#!/usr/bin/env bash
# Build an unsigned arm64 SanPy.app in a new dated dist folder.
set -euo pipefail

cd "$(dirname "$0")"
# shellcheck source=config.sh
source ./config.sh

if [[ "$(uname -m)" != "${ARCH}" ]]; then
  echo "error: packaging/macos is ${ARCH}-only (got $(uname -m))" >&2
  exit 1
fi

if ! command -v uv >/dev/null 2>&1; then
  echo "error: uv not found on PATH" >&2
  exit 1
fi

if [[ -x "${PYTHON}" ]]; then
  VENV_PYTHON_VERSION="$("${PYTHON}" -c 'import platform; print(platform.python_version())')"
else
  VENV_PYTHON_VERSION=""
fi

if [[ "${VENV_PYTHON_VERSION}" != "${PYTHON_VERSION}" ]]; then
  echo "==> creating .venv with Python ${PYTHON_VERSION}"
  uv venv --clear --python "${PYTHON_VERSION}" "${VENV}"
fi

"${PYTHON}" -c "
import platform
import sys
machine = platform.machine()
if machine != '${ARCH}':
    raise SystemExit(f'error: venv is not ${ARCH} (got {machine})')
if platform.python_version() != '${PYTHON_VERSION}':
    raise SystemExit(f'error: expected Python ${PYTHON_VERSION} (got {platform.python_version()})')
print(sys.executable)
print(sys.version)
print('machine', machine)
"

echo "==> syncing locked build environment"
uv pip sync --python "${PYTHON}" --strict "${LOCK_FILE}"

echo "==> dependency compatibility gate"
uv pip check --python "${PYTHON}"

echo "==> import gate"
"${PYTHON}" -c "
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

mkdir -p "${DIST_ROOT}" "${BUILD_ROOT}"
RUN_DATE="$(date +%Y%m%d)"
RUN_NUMBER=1
while [[ -e "${DIST_ROOT}/${RUN_DATE}_v${RUN_NUMBER}" ]]; do
  RUN_NUMBER=$((RUN_NUMBER + 1))
done
RUN_NAME="${RUN_DATE}_v${RUN_NUMBER}"
RUN_DIR="${DIST_ROOT}/${RUN_NAME}"
WORK_DIR="${BUILD_ROOT}/${RUN_NAME}"
mkdir -p "${RUN_DIR}" "${WORK_DIR}"

echo "==> pyinstaller"
SANPY_ARCH="${ARCH}" \
SANPY_BUNDLE_ID="${BUNDLE_ID}" \
SANPY_MIN_MACOS_VERSION="${MIN_MACOS_VERSION}" \
"${PYINSTALLER}" --noconfirm --clean \
  --distpath "${RUN_DIR}" \
  --workpath "${WORK_DIR}" \
  sanpy.spec

APP="${RUN_DIR}/${APP_NAME}.app"
if [[ ! -d "${APP}" ]]; then
  echo "error: expected ${APP}" >&2
  exit 1
fi

printf '%s\n' "${RUN_NAME}" > "${DIST_ROOT}/.latest.txt.tmp"
mv "${DIST_ROOT}/.latest.txt.tmp" "${LATEST_FILE}"

echo "run:          ${RUN_NAME}"
echo "unsigned app: ${APP}"
echo "smoke test:   open ${APP}"
