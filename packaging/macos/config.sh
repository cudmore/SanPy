#!/usr/bin/env bash

PACKAGING_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${PACKAGING_DIR}/../.." && pwd)"

APP_NAME="SanPy"
ARCH="arm64"
PYTHON_VERSION="3.11.14"
BUNDLE_ID="org.sanpy.SanPy"
MIN_MACOS_VERSION="11.0"
TEAM_ID="794C773KDS"

VENV="${PACKAGING_DIR}/.venv"
PYTHON="${VENV}/bin/python"
PYINSTALLER="${VENV}/bin/pyinstaller"
LOCK_FILE="${PACKAGING_DIR}/requirements-macos-arm64-py311.txt"
DIST_ROOT="${PACKAGING_DIR}/dist"
BUILD_ROOT="${PACKAGING_DIR}/build"
LATEST_FILE="${DIST_ROOT}/latest.txt"
ENTITLEMENTS="${PACKAGING_DIR}/entitlements.plist"
