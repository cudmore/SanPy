#!/usr/bin/env bash

PACKAGING_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${PACKAGING_DIR}/../.." && pwd)"

APP_NAME="SanPy"
ARCH="arm64"
PYTHON_VERSION="$(<"${REPO_ROOT}/.python-version")"
BUNDLE_ID="org.sanpy.SanPy"
MIN_MACOS_VERSION="11.0"
TEAM_ID="794C773KDS"

VENV="${PACKAGING_DIR}/.venv"
PYTHON="${VENV}/bin/python"
PYINSTALLER="${VENV}/bin/pyinstaller"
DIST_ROOT="${PACKAGING_DIR}/dist"
BUILD_ROOT="${PACKAGING_DIR}/build"
LATEST_FILE="${DIST_ROOT}/latest.txt"
ENTITLEMENTS="${PACKAGING_DIR}/entitlements.plist"
