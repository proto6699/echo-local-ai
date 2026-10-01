#!/usr/bin/env bash
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
echo '== Den =='
if docker info >/dev/null 2>&1; then
  docker compose ps
else
  sudo docker compose ps
fi
echo
echo '== Neco =='
systemctl --user --no-pager --full status echo-local-ai-v2-neco.service || true
