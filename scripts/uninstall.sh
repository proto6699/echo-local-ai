#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo 'This removes the v2 service and container. Den data is kept unless you choose to delete it.'
systemctl --user disable --now echo-local-ai-v2-neco.service 2>/dev/null || true
rm -f "$HOME/.config/systemd/user/echo-local-ai-v2-neco.service"
systemctl --user daemon-reload

if docker info >/dev/null 2>&1; then
  COMPOSE=(docker compose)
else
  COMPOSE=(sudo docker compose)
fi

printf 'Delete the saved Den Docker volume too? [y/N] '
read -r answer
if [[ "$answer" =~ ^[Yy]$ ]]; then
  "${COMPOSE[@]}" down -v
else
  "${COMPOSE[@]}" down
fi

echo 'Local .env and .runtime files were left in the repo folder.'
