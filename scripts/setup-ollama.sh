#!/usr/bin/env bash
# Optional convenience path: expose host Ollama to Docker and pull NECO_MODEL.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
[[ -f .env ]] || { echo 'Run ./install.sh first.' >&2; exit 1; }
command -v ollama >/dev/null 2>&1 || {
  echo 'Ollama is missing. Install it or configure another OpenAI-compatible backend in Open WebUI.' >&2
  exit 1
}

MODEL="$(python3 -c 'from neco.config import Settings; print(Settings.from_env().model)')"
echo "Configuring host Ollama for the Docker bridge. Selected model: $MODEL"
echo 'SECURITY: this binds Ollama to 0.0.0.0:11434 so Docker can reach it.'
echo 'Keep TCP 11434 blocked from untrusted LAN/WAN clients with your firewall.'
sudo mkdir -p /etc/systemd/system/ollama.service.d
printf '[Service]\nEnvironment="OLLAMA_HOST=0.0.0.0:11434"\n' \
  | sudo tee /etc/systemd/system/ollama.service.d/echo-local-ai-v2.conf >/dev/null
sudo systemctl daemon-reload
sudo systemctl enable --now ollama
sudo systemctl restart ollama

ready=false
for _ in {1..20}; do
  if OLLAMA_HOST=127.0.0.1:11434 ollama list >/dev/null 2>&1; then ready=true; break; fi
  sleep 1
done
[[ "$ready" == true ]] || { echo 'Ollama did not become ready. Check journalctl -u ollama.' >&2; exit 1; }
OLLAMA_HOST=127.0.0.1:11434 ollama pull "$MODEL"
echo 'Ollama model ready.'
