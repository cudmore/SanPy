#!/usr/bin/env bash
# Developer ID sign of the existing unsigned (ad-hoc) SanPy.app.
# Fail fast. No notary, no staple, no rebuild.
set -euo pipefail

cd "$(dirname "$0")"

APP="dist/SanPy.app"
ENTITLEMENTS="entitlements.plist"

if [[ ! -d "${APP}" ]]; then
  echo "error: ${APP} not found. Run ./build_local.sh first." >&2
  exit 1
fi

if [[ ! -f "${ENTITLEMENTS}" ]]; then
  echo "error: ${ENTITLEMENTS} not found." >&2
  exit 1
fi

if [[ ! -f _secrets.py ]]; then
  echo "error: _secrets.py not found." >&2
  exit 1
fi

IDENTITY="$(python3 -c "from _secrets import app_certificate; print(app_certificate)")"
if [[ -z "${IDENTITY}" ]]; then
  echo "error: app_certificate is empty in _secrets.py" >&2
  exit 1
fi

echo "==> signing as: ${IDENTITY}"
echo "==> app: ${PWD}/${APP}"

# Runtime logs land in the bundle (frozen logger uses sys._MEIPASS). codesign rejects them.
find "${APP}" -name .DS_Store -delete
find "${APP}" \( -name '*.log' -o -name '*.log.*' -o -name 'sanpy.log*' \) -delete

# Sign nested Mach-O first (not the main executable). Then sign the bundle. No --deep.
MAIN_BIN="${APP}/Contents/MacOS/SanPy"
signed=0
while IFS= read -r -d '' f; do
  if [[ "${f}" == "${MAIN_BIN}" ]]; then
    continue
  fi
  if file -b "${f}" | grep -q 'Mach-O'; then
    if ! out="$(codesign --force --options runtime --timestamp \
      --entitlements "${ENTITLEMENTS}" \
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
codesign --verify --verbose "${APP}"

echo "==> codesign -dv"
codesign -dv --verbose=2 "${APP}" 2>&1 | tee /tmp/sanpy-codesign-dv.txt

# codesign --verify succeeds for ad-hoc too. Require Developer ID.
if grep -q 'Signature=adhoc' /tmp/sanpy-codesign-dv.txt; then
  echo "error: still ad-hoc; Developer ID sign did not take" >&2
  exit 1
fi
if ! grep -q 'Authority=Developer ID Application: Robert Cudmore' /tmp/sanpy-codesign-dv.txt; then
  echo "error: Authority is not Developer ID Application" >&2
  exit 1
fi

echo "signed: ${PWD}/${APP}"
echo "smoke test: open ${PWD}/${APP}"
