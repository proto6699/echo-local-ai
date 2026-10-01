#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[[ -f "$ROOT/.env" ]] || { echo "Run ./install.sh first."; exit 1; }
[[ -s "$ROOT/.runtime/neco_token" ]] || { echo "Run ./scripts/set-token.sh first."; exit 1; }
set -a
# shellcheck disable=SC1091
source "$ROOT/.env"
set +a
export NECO_TOKEN_FILE="$ROOT/.runtime/neco_token"
export NECO_STATE_FILE="$ROOT/.runtime/neco_state.json"
cd "$ROOT"
exec "$ROOT/neco/.venv/bin/python" -m neco.runtime --test
