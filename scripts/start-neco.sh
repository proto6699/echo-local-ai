#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[[ -f "$ROOT/.runtime/neco_token" ]] || { echo "Run ./scripts/set-token.sh first."; exit 1; }
systemctl --user daemon-reload
systemctl --user enable --now echo-local-ai-neco.service
systemctl --user --no-pager --full status echo-local-ai-neco.service || true
