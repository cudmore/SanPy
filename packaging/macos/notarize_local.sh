#!/usr/bin/env bash
# Notarize the Developer ID-signed SanPy.app, then staple.
# Source of truth: Apple "Customizing the notarization workflow"
#   ditto zip -> notarytool submit --wait -> stapler staple the .app -> new zip
# Do not re-sign after notarize (cdhash would change; stapler error 65).
set -euo pipefail

cd "$(dirname "$0")"

APP="dist/SanPy.app"
ZIP_SUBMIT="dist/SanPy-submit.zip"
ZIP_DIST="dist/SanPy-macos-arm64.zip"
ID_FILE="dist/notary-submission-id.txt"

if [[ ! -f _secrets.py ]]; then
  echo "error: _secrets.py not found." >&2
  exit 1
fi

eval "$(python3 - <<'PY'
from _secrets import notary_profile, email, team_id, app_password
import shlex
print(f"NOTARY_PROFILE={shlex.quote(notary_profile)}")
print(f"APPLE_ID={shlex.quote(email)}")
print(f"TEAM_ID={shlex.quote(team_id)}")
print(f"APP_PASSWORD={shlex.quote(app_password)}")
PY
)"

usage() {
  echo "usage: $0 [--wait-id SUBMISSION-UUID]" >&2
  echo "  default: re-sign (cleans smoke-test logs), zip, submit --wait, staple" >&2
  echo "  --wait-id: resume wait+staple after a wifi drop (upload already succeeded)" >&2
  exit 2
}

WAIT_ID=""
if [[ "${1:-}" == "--wait-id" ]]; then
  WAIT_ID="${2:-}"
  if [[ -z "${WAIT_ID}" ]]; then
    usage
  fi
elif [[ -n "${1:-}" ]]; then
  usage
fi

auth_args() {
  if xcrun notarytool history --keychain-profile "${NOTARY_PROFILE}" >/dev/null 2>&1; then
    echo "==> auth: keychain profile ${NOTARY_PROFILE}" >&2
    printf -- '--keychain-profile\t%s\n' "${NOTARY_PROFILE}"
  else
    echo "==> auth: apple-id from _secrets.py (keychain profile '${NOTARY_PROFILE}' not on this Mac)" >&2
    printf -- '--apple-id\t%s\n--team-id\t%s\n--password\t%s\n' \
      "${APPLE_ID}" "${TEAM_ID}" "${APP_PASSWORD}"
  fi
}

read_auth() {
  AUTH=()
  while IFS=$'\t' read -r k v; do
    AUTH+=("${k}" "${v}")
  done < <(auth_args)
}

parse_json_field() {
  python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get(sys.argv[1], '') or '')" "$1"
}

wait_for_id() {
  local id="$1"
  echo "==> notarytool wait ${id}"
  local json
  json="$(xcrun notarytool wait "${id}" "${AUTH[@]}" \
    --output-format json --timeout 45m)"
  echo "${json}"
  local status
  status="$(printf '%s' "${json}" | parse_json_field status)"
  echo "==> notary status: ${status}"
  if [[ "${status}" != "Accepted" ]]; then
    echo "error: notary did not Accept (status=${status}). Log:" >&2
    xcrun notarytool log "${id}" "${AUTH[@]}" >&2 || true
    exit 1
  fi
}

staple_and_zip() {
  echo "==> stapler staple ${APP}"
  xcrun stapler staple "${APP}"
  xcrun stapler validate "${APP}"
  echo "==> distribution zip ${ZIP_DIST}"
  rm -f "${ZIP_DIST}"
  ditto -c -k --sequesterRsrc --keepParent "${APP}" "${ZIP_DIST}"
  echo "stapled app: ${PWD}/${APP}"
  echo "distribute:  ${PWD}/${ZIP_DIST}"
}

read_auth

if [[ -n "${WAIT_ID}" ]]; then
  echo "${WAIT_ID}" > "${ID_FILE}"
  wait_for_id "${WAIT_ID}"
  staple_and_zip
  exit 0
fi

if [[ ! -d "${APP}" ]]; then
  echo "error: ${APP} not found. Run ./build_local.sh then ./_sign_local.sh first." >&2
  exit 1
fi

# Smoke tests write sanpy.log into the bundle and break the seal. Re-sign first.
echo "==> _sign_local.sh (required before zip/submit)"
./_sign_local.sh

echo "==> zip for notary (ditto --keepParent)"
rm -f "${ZIP_SUBMIT}"
ditto -c -k --keepParent "${APP}" "${ZIP_SUBMIT}"

echo "==> notarytool submit --wait"
submit_json=""
attempt=1
max_attempts=3
while (( attempt <= max_attempts )); do
  echo "    attempt ${attempt}/${max_attempts}"
  if submit_json="$(xcrun notarytool submit "${ZIP_SUBMIT}" "${AUTH[@]}" \
      --wait --timeout 45m --output-format json)"; then
    break
  fi
  echo "    submit failed (wifi/upload). ${attempt}/${max_attempts}" >&2
  if [[ -n "${submit_json}" ]]; then
    maybe_id="$(printf '%s' "${submit_json}" | parse_json_field id || true)"
    if [[ -n "${maybe_id}" ]]; then
      echo "${maybe_id}" > "${ID_FILE}"
      echo "    submission id ${maybe_id} — waiting instead of re-upload" >&2
      wait_for_id "${maybe_id}"
      staple_and_zip
      exit 0
    fi
  fi
  if (( attempt == max_attempts )); then
    echo "error: notarytool submit failed after ${max_attempts} attempts." >&2
    echo "  if upload finished, resume with: $0 --wait-id <uuid>" >&2
    exit 1
  fi
  attempt=$((attempt + 1))
  sleep 5
done

echo "${submit_json}"
sub_id="$(printf '%s' "${submit_json}" | parse_json_field id)"
status="$(printf '%s' "${submit_json}" | parse_json_field status)"
if [[ -n "${sub_id}" ]]; then
  echo "${sub_id}" > "${ID_FILE}"
  echo "==> submission id: ${sub_id}"
fi
echo "==> notary status: ${status}"

if [[ "${status}" != "Accepted" ]]; then
  echo "error: notary did not Accept (status=${status}). Log:" >&2
  if [[ -n "${sub_id}" ]]; then
    xcrun notarytool log "${sub_id}" "${AUTH[@]}" >&2 || true
  fi
  exit 1
fi

staple_and_zip
