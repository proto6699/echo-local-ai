#!/usr/bin/env bash
# Authenticated final step after the first Open WebUI account/API key exists.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
[[ -f .env && -x neco/.venv/bin/python ]] || { echo 'Run ./install.sh first.' >&2; exit 1; }

TOKEN_FILE="$(python3 -c 'from neco.config import Settings; print(Settings.from_env().token_file)')"
if [[ -s "$TOKEN_FILE" ]]; then
  echo '[+] using saved API key'
else
  ./scripts/set-token.sh
fi

python3 scripts/setup-persona.py
./scripts/test-neco.sh
loginctl enable-linger "$(id -un)"
./scripts/start-neco.sh
./scripts/doctor.sh

echo
echo 'Neco v2 is resident. Closing the browser will not stop the user service.'
