#!/usr/bin/env bash
# Build an unsigned arm64 SanPy.app in a version-named dist folder.
set -euo pipefail

cd "$(dirname "$0")"
# shellcheck source=config.sh
source ./config.sh

GIT_STATUS="$(git -C "${REPO_ROOT}" status --porcelain --untracked-files=normal)"
if [[ -n "${GIT_STATUS}" ]]; then
  echo "error: refusing to build because the Git working tree is not clean:" >&2
  printf '%s\n' "${GIT_STATUS}" >&2
  echo "Commit, stash, or remove these changes before building." >&2
  exit 1
fi

if [[ "$(uname -m)" != "${ARCH}" ]]; then
  echo "error: packaging/macos is ${ARCH}-only (got $(uname -m))" >&2
  exit 1
fi

if ! command -v uv >/dev/null 2>&1; then
  echo "error: uv not found on PATH" >&2
  exit 1
fi
if ! command -v npm >/dev/null 2>&1; then
  echo "error: npm not found on PATH; install Node.js/npm first" >&2
  exit 1
fi
if [[ ! -d "${NICEPOOL_PROJECT}" ]]; then
  echo "error: NicePool project not found: ${NICEPOOL_PROJECT}" >&2
  exit 1
fi
if [[ ! -f "${MAPMANAGER_REPO}/package-lock.json" ]]; then
  echo "error: npm lock file not found: ${MAPMANAGER_REPO}/package-lock.json" >&2
  exit 1
fi

MAPMANAGER_STATUS="$(git -C "${MAPMANAGER_REPO}" status --porcelain --untracked-files=normal)"
if [[ -n "${MAPMANAGER_STATUS}" ]]; then
  echo "error: refusing to build because mapmanager-web-components is not clean:" >&2
  printf '%s\n' "${MAPMANAGER_STATUS}" >&2
  echo "Commit or remove those changes, then rebuild the NicePool frontend." >&2
  exit 1
fi
MAPMANAGER_COMMIT="$(git -C "${MAPMANAGER_REPO}" rev-parse HEAD)"

echo "==> building NicePool frontend"
npm --prefix "${MAPMANAGER_REPO}" run build \
  --workspace @mapmanager/nicepool-pyqt5-frontend

for NICEPOOL_ASSET in \
  "${NICEPOOL_STATIC}/index.html" \
  "${NICEPOOL_STATIC}/nicepool-pyqt5.js" \
  "${NICEPOOL_STATIC}/nicepool-pyqt5.css" \
  "${NICEPOOL_BUILD_INFO}"; do
  if [[ ! -f "${NICEPOOL_ASSET}" ]]; then
    echo "error: NicePool frontend asset not found: ${NICEPOOL_ASSET}" >&2
    exit 1
  fi
done

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

NICEPOOL_FRONTEND_VERSION="$("${PYTHON}" -c "
import json
from pathlib import Path

build_info = json.loads(Path('${NICEPOOL_BUILD_INFO}').read_text(encoding='utf-8'))
if build_info.get('schema_version') != 1:
    raise SystemExit('error: unsupported NicePool build information schema')
if build_info.get('repository_commit') != '${MAPMANAGER_COMMIT}':
    raise SystemExit('error: NicePool frontend assets do not match mapmanager-web-components HEAD')
if build_info.get('frontend_package') != '@mapmanager/nicepool-pyqt5-frontend':
    raise SystemExit('error: unexpected NicePool frontend package in build information')
print(build_info['frontend_version'])
")"

echo "==> syncing locked build environment"
UV_PROJECT_ENVIRONMENT="${VENV}" uv sync \
  --project "${REPO_ROOT}" \
  --locked \
  --extra gui \
  --no-dev \
  --group packaging \
  --python "${PYTHON_VERSION}" \
  --reinstall-package sanpy-ephys

echo "==> installing NicePool adapter"
uv pip install --python "${PYTHON}" --no-deps "${NICEPOOL_PROJECT}"

echo "==> dependency compatibility gate"
uv pip check --python "${PYTHON}"

echo "==> import gate"
"${PYTHON}" -c "
from PyQt5 import QtCore
from PyQt5 import QtWebEngineWidgets
from importlib.metadata import version
from pathlib import Path
import numpy
import pandas
import scipy
import tables
import skimage
import h5py
import sanpy
import nicepool_pyqt5
static_directory = Path(nicepool_pyqt5.__file__).resolve().parent / 'static'
for filename in ('index.html', 'nicepool-pyqt5.js', 'nicepool-pyqt5.css', 'nicepool-build-info.json'):
    path = static_directory / filename
    if not path.is_file():
        raise SystemExit(f'error: installed NicePool asset not found: {path}')
print('PyQt5', QtCore.PYQT_VERSION_STR)
print('PyQtWebEngine', version('PyQtWebEngine'))
print('nicepool-pyqt5', version('nicepool-pyqt5'))
print('numpy', numpy.__version__)
print('pandas', pandas.__version__)
print('scipy', scipy.__version__)
print('tables', tables.__version__)
print('skimage', skimage.__version__)
print('h5py', h5py.__version__)
print('sanpy', sanpy.__version__)
"

INSTALLED_SANPY_VERSION="$("${PYTHON}" -c \
  'from importlib.metadata import version; print(version("sanpy-ephys"))')"

mkdir -p "${DIST_ROOT}" "${BUILD_ROOT}"
RUN_NAME="${INSTALLED_SANPY_VERSION}"
RUN_DIR="${DIST_ROOT}/${RUN_NAME}"
WORK_DIR="${BUILD_ROOT}/${RUN_NAME}"
if [[ -e "${RUN_DIR}" || -e "${WORK_DIR}" ]]; then
  echo "error: refusing to overwrite existing build version ${RUN_NAME}" >&2
  echo "Remove incomplete build and dist directories before rebuilding the same commit." >&2
  exit 1
fi
mkdir -p "${RUN_DIR}" "${WORK_DIR}"

GIT_COMMIT="$(git -C "${REPO_ROOT}" rev-parse HEAD)"
BUILD_INFO_PATH="${RUN_DIR}/build_info.json"
ENVIRONMENT_PATH="${RUN_DIR}/environment.txt"
SOURCE_ARCHIVE="${RUN_DIR}/source-${GIT_COMMIT}.zip"

echo "==> recording build info"
"${PYTHON}" ../create_build_info.py \
  --output "${BUILD_INFO_PATH}" \
  --mapmanager-commit "${MAPMANAGER_COMMIT}" \
  --nicepool-frontend-version "${NICEPOOL_FRONTEND_VERSION}"

RECORDED_SANPY_VERSION="$("${PYTHON}" -c \
  'import json, sys; print(json.load(open(sys.argv[1]))["build"]["sanpy_version"])' \
  "${BUILD_INFO_PATH}")"
if [[ "${RECORDED_SANPY_VERSION}" != "${INSTALLED_SANPY_VERSION}" ]]; then
  echo "error: build metadata version ${RECORDED_SANPY_VERSION} does not match installed SanPy ${INSTALLED_SANPY_VERSION}" >&2
  exit 1
fi

echo "==> recording installed environment"
uv pip freeze \
  --python "${PYTHON}" \
  --exclude-editable > "${ENVIRONMENT_PATH}"

echo "==> archiving exact committed source"
git -C "${REPO_ROOT}" archive \
  --format=zip \
  --output="${SOURCE_ARCHIVE}" \
  "${GIT_COMMIT}"

echo "==> pyinstaller"
SANPY_ARCH="${ARCH}" \
SANPY_BUNDLE_ID="${BUNDLE_ID}" \
SANPY_MIN_MACOS_VERSION="${MIN_MACOS_VERSION}" \
SANPY_BUILD_INFO="${BUILD_INFO_PATH}" \
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
echo "build info:   ${BUILD_INFO_PATH}"
echo "environment:  ${ENVIRONMENT_PATH}"
echo "source:       ${SOURCE_ARCHIVE}"
echo "smoke test:   open ${APP}"
