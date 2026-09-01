#!/usr/bin/env bash
# Sign the latest build, notarize it, staple it, and create the distribution zip.
set -euo pipefail

cd "$(dirname "$0")"
# shellcheck source=config.sh
source ./config.sh

if [[ ! -f "${LATEST_FILE}" ]]; then
  echo "error: ${LATEST_FILE} not found. Run ./build_local.sh first." >&2
  exit 1
fi
RUN_NAME="$(<"${LATEST_FILE}")"
RUN_DIR="${DIST_ROOT}/${RUN_NAME}"
APP="${RUN_DIR}/${APP_NAME}.app"
ZIP_SUBMIT="${RUN_DIR}/${APP_NAME}-submit.zip"
ID_FILE="${RUN_DIR}/notary-submission-id.txt"
NOTARY_LOG="${RUN_DIR}/notary-log.json"

if [[ ! -d "${APP}" ]]; then
  echo "error: ${APP} not found. Run ./build_local.sh first." >&2
  exit 1
fi
if [[ ! -f "${PACKAGING_DIR}/_secrets.py" ]]; then
  echo "error: _secrets.py not found." >&2
  exit 1
fi

NOTARY_PROFILE="$(python3 -c "from _secrets import notary_profile; print(notary_profile)")"
if [[ -z "${NOTARY_PROFILE}" ]]; then
  echo "error: notary_profile is empty in _secrets.py" >&2
  exit 1
fi
AUTH=(--keychain-profile "${NOTARY_PROFILE}")

usage() {
  echo "usage: $0 [--wait-id SUBMISSION-UUID]" >&2
  exit 2
}

WAIT_ID=""
if [[ "${1:-}" == "--wait-id" ]]; then
  WAIT_ID="${2:-}"
  [[ -n "${WAIT_ID}" ]] || usage
elif [[ -n "${1:-}" ]]; then
  usage
fi

json_field() {
  python3 -c "import json,sys; print(json.load(sys.stdin).get(sys.argv[1], '') or '')" "$1"
}

wait_for_id() {
  local id="$1"
  echo "==> waiting for notarization: ${id}"
  local result status
  result="$(xcrun notarytool wait "${id}" "${AUTH[@]}" \
    --output-format json --timeout 45m)"
  echo "${result}"
  status="$(printf '%s' "${result}" | json_field status)"
  if [[ "${status}" != "Accepted" ]]; then
    echo "error: notarization status is ${status}" >&2
    xcrun notarytool log "${id}" "${AUTH[@]}" "${NOTARY_LOG}" >&2 || true
    exit 1
  fi
  xcrun notarytool log "${id}" "${AUTH[@]}" "${NOTARY_LOG}" >/dev/null || true
}

finish_release() {
  echo "==> stapling ticket"
  xcrun stapler staple "${APP}"
  xcrun stapler validate "${APP}"
  codesign --verify --deep --strict --verbose=2 "${APP}"
  spctl --assess --type execute --verbose=2 "${APP}"

  local app_version zip_dist
  app_version="$(plutil -extract CFBundleShortVersionString raw "${APP}/Contents/Info.plist")"
  zip_dist="${RUN_DIR}/${APP_NAME}-macos-${ARCH}-${app_version}.zip"
  echo "==> distribution zip: ${zip_dist}"
  rm -f "${zip_dist}" "${zip_dist}.sha256"
  ditto -c -k --sequesterRsrc --keepParent "${APP}" "${zip_dist}"
  shasum -a 256 "${zip_dist}" > "${zip_dist}.sha256"
  rm -f "${ZIP_SUBMIT}"
  echo "run:        ${RUN_NAME}"
  echo "stapled:    ${APP}"
  echo "distribute: ${zip_dist}"
  echo "checksum:   ${zip_dist}.sha256"
}

echo "==> run: ${RUN_NAME}"
echo "==> auth: keychain profile ${NOTARY_PROFILE}"

if [[ -n "${WAIT_ID}" ]]; then
  printf '%s\n' "${WAIT_ID}" > "${ID_FILE}"
  wait_for_id "${WAIT_ID}"
  finish_release
  exit 0
fi

echo "==> signing"
./_sign_local.sh "${RUN_NAME}"

echo "==> submission zip"
rm -f "${ZIP_SUBMIT}"
ditto -c -k --keepParent "${APP}" "${ZIP_SUBMIT}"

echo "==> uploading to Apple"
submit_json=""
submission_id=""
for attempt in 1 2 3; do
  echo "    upload attempt ${attempt}/3"
  if submit_json="$(xcrun notarytool submit "${ZIP_SUBMIT}" "${AUTH[@]}" \
      --no-wait --output-format json)"; then
    submission_id="$(printf '%s' "${submit_json}" | json_field id)"
    if [[ -n "${submission_id}" ]]; then
      break
    fi
  fi
  if (( attempt < 3 )); then
    sleep 5
  fi
done

if [[ -z "${submission_id}" ]]; then
  echo "error: upload failed without a submission id" >&2
  exit 1
fi

echo "${submit_json}"
printf '%s\n' "${submission_id}" > "${ID_FILE}"
echo "==> submission id saved: ${submission_id}"
wait_for_id "${submission_id}"
finish_release
