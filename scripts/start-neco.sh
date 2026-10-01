#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
TOKEN_FILE="$(python3 -c 'from neco.config import Settings; print(Settings.from_env().token_file)')"
[[ -s "$TOKEN_FILE" ]] || { echo 'Run ./scripts/set-token.sh first.' >&2; exit 1; }
systemctl --user daemon-reload
systemctl --user enable --now echo-local-ai-v2-neco.service
systemctl --user --no-pager --full status echo-local-ai-v2-neco.service || true
