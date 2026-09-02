#!/usr/bin/env bash
# Regenerate the committed dependency lock used by build_local.sh.
set -euo pipefail

cd "$(dirname "$0")"
# shellcheck source=config.sh
source ./config.sh

if ! command -v uv >/dev/null 2>&1; then
  echo "error: uv not found on PATH" >&2
  exit 1
fi

echo "==> updating macOS ${ARCH} Python ${PYTHON_VERSION} build lock"
LOCK_FILE_NAME="${LOCK_FILE##*/}"
uv pip compile requirements-build.in \
  --python-version "${PYTHON_VERSION}" \
  --python-platform aarch64-apple-darwin \
  --output-file "${LOCK_FILE_NAME}"

echo "updated: ${LOCK_FILE}"
