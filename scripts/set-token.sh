#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
TOKEN_FILE="$(python3 -c 'from neco.config import Settings; print(Settings.from_env().token_file)')"
mkdir -p "$(dirname "$TOKEN_FILE")"
chmod 700 "$(dirname "$TOKEN_FILE")"
printf 'Open WebUI API key: '
IFS= read -r -s TOKEN
printf '\n'
[[ -n "$TOKEN" ]] || { echo 'No token entered.' >&2; exit 1; }
printf '%s' "$TOKEN" > "$TOKEN_FILE"
chmod 600 "$TOKEN_FILE"
echo "Token saved to $TOKEN_FILE."
