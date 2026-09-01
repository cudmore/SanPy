#!/usr/bin/env bash
# Developer ID sign of the existing unsigned (ad-hoc) SanPy.app.
# Fail fast. No notary, no staple, no rebuild.
set -euo pipefail

cd "$(dirname "$0")"
# shellcheck source=config.sh
source ./config.sh

RUN_NAME="${1:-}"
if [[ -z "${RUN_NAME}" ]]; then
  if [[ ! -f "${LATEST_FILE}" ]]; then
    echo "error: ${LATEST_FILE} not found. Run ./build_local.sh first." >&2
    exit 1
  fi
  RUN_NAME="$(<"${LATEST_FILE}")"
fi

RUN_DIR="${DIST_ROOT}/${RUN_NAME}"
APP="${RUN_DIR}/${APP_NAME}.app"

if [[ ! -d "${APP}" ]]; then
  echo "error: ${APP} not found. Run ./build_local.sh first." >&2
  exit 1
fi

if [[ ! -f "${ENTITLEMENTS}" ]]; then
  echo "error: ${ENTITLEMENTS} not found." >&2
  exit 1
fi

if [[ ! -f "${PACKAGING_DIR}/_secrets.py" ]]; then
  echo "error: _secrets.py not found." >&2
  exit 1
fi

IDENTITY="$(python3 -c "from _secrets import app_certificate; print(app_certificate)")"
if [[ -z "${IDENTITY}" ]]; then
  echo "error: app_certificate is empty in _secrets.py" >&2
  exit 1
fi

echo "==> signing as: ${IDENTITY}"
echo "==> run: ${RUN_NAME}"
echo "==> app: ${APP}"

# Sign nested Mach-O files without app entitlements, then sign the bundle.
MAIN_BIN="${APP}/Contents/MacOS/${APP_NAME}"
signed=0
while IFS= read -r -d '' f; do
  if [[ "${f}" == "${MAIN_BIN}" ]]; then
    continue
  fi
  if file -b "${f}" | grep -q 'Mach-O'; then
    if ! out="$(codesign --force --options runtime --timestamp \
      --sign "${IDENTITY}" \
      "${f}" 2>&1)"; then
      echo "${out}" >&2
      echo "error: codesign failed: ${f}" >&2
      exit 1
    fi
    signed=$((signed + 1))
    if (( signed % 50 == 0 )); then
      echo "    signed ${signed} nested binaries ..."
    fi
  fi
done < <(find "${APP}" -type f -print0)
echo "==> signed ${signed} nested binaries"

echo "==> signing bundle"
codesign --force --options runtime --timestamp \
  --entitlements "${ENTITLEMENTS}" \
  --sign "${IDENTITY}" \
  "${APP}"

echo "==> codesign --verify"
codesign --verify --deep --strict --verbose=2 "${APP}"

echo "==> codesign -dv"
SIGN_DETAILS="$(codesign -dv --verbose=2 "${APP}" 2>&1)"
echo "${SIGN_DETAILS}"

# codesign --verify succeeds for ad-hoc too. Require Developer ID.
if grep -q 'Signature=adhoc' <<<"${SIGN_DETAILS}"; then
  echo "error: still ad-hoc; Developer ID sign did not take" >&2
  exit 1
fi
if ! grep -q 'Authority=Developer ID Application:' <<<"${SIGN_DETAILS}"; then
  echo "error: signature is not Developer ID Application" >&2
  exit 1
fi
if ! grep -q "TeamIdentifier=${TEAM_ID}" <<<"${SIGN_DETAILS}"; then
  echo "error: signature TeamIdentifier is not ${TEAM_ID}" >&2
  exit 1
fi

echo "signed: ${APP}"
echo "smoke test: open ${APP}"
