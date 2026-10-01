#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
WITH_OLLAMA=false
[[ "${1:-}" == "--ollama" ]] && WITH_OLLAMA=true

say() { printf '%s\n' "$*"; }
die() { printf 'error: %s\n' "$*" >&2; exit 1; }

install_host_deps() {
  if command -v docker >/dev/null 2>&1 \
    && (docker compose version >/dev/null 2>&1 || command -v docker-compose >/dev/null 2>&1) \
    && command -v python3 >/dev/null 2>&1 \
    && python3 -m venv --help >/dev/null 2>&1; then
    return
  fi

  [[ -r /etc/os-release ]] || die "Can't identify this Linux distribution."
  # shellcheck disable=SC1091
  source /etc/os-release
  family="${ID:-} ${ID_LIKE:-}"
  echo 'Some host dependencies are missing.'
  printf 'Install Docker / Compose / Python bits now? [Y/n] '
  read -r answer
  answer="${answer:-Y}"
  [[ "$answer" =~ ^([Yy]|[Yy][Ee][Ss])$ ]] || die 'Install cancelled.'

  if [[ "$family" == *arch* ]]; then
    sudo pacman -Syu --needed docker docker-compose python
  elif [[ "$family" == *ubuntu* || "$family" == *debian* ]]; then
    sudo apt-get update
    sudo apt-get install -y docker.io python3 python3-venv
    sudo apt-get install -y docker-compose-v2 || sudo apt-get install -y docker-compose
  else
    die 'Automatic dependency install supports Arch-family and Debian-family Linux. Install Docker, Compose, Python 3 + venv, then rerun.'
  fi
}

install_host_deps
command -v docker >/dev/null 2>&1 || die 'Docker is unavailable.'
command -v python3 >/dev/null 2>&1 || die 'Python 3 is unavailable.'
command -v systemctl >/dev/null 2>&1 || die 'systemd/systemctl is required.'

[[ -f neco/runtime.py && -f neco/config.py ]] || die 'Neco v2 runtime files are missing.'
[[ -f openwebui/overlay/index.html ]] || die 'Den overlay is missing.'

if ! sudo systemctl is-active --quiet docker; then
  say '[+] starting Docker'
  sudo systemctl reset-failed docker 2>/dev/null || true
  sudo systemctl enable --now docker || {
    sudo journalctl -u docker.service -n 60 --no-pager || true
    die 'Docker failed to start.'
  }
else
  sudo systemctl enable docker >/dev/null
fi

if docker info >/dev/null 2>&1; then
  DOCKER=(docker)
else
  DOCKER=(sudo docker)
  say '[i] using sudo for Docker during installation'
  say '[i] optional: sudo usermod -aG docker "$USER" then log out/in'
fi

if "${DOCKER[@]}" compose version >/dev/null 2>&1; then
  compose() { "${DOCKER[@]}" compose "$@"; }
elif command -v docker-compose >/dev/null 2>&1; then
  compose() {
    if [[ "${DOCKER[0]}" == sudo ]]; then sudo docker-compose "$@"; else docker-compose "$@"; fi
  }
else
  die 'Docker Compose is unavailable.'
fi

if [[ ! -f .env ]]; then
  cp .env.example .env
  say '[+] created .env'
fi

python3 - .env <<'PY'
from pathlib import Path
import secrets
import sys
p = Path(sys.argv[1])
lines = p.read_text().splitlines()
out = []
found = False
for line in lines:
    if line.startswith("WEBUI_SECRET_KEY="):
        found = True
        if not line.split("=", 1)[1].strip():
            line = "WEBUI_SECRET_KEY=" + secrets.token_hex(32)
    out.append(line)
if not found:
    out.append("WEBUI_SECRET_KEY=" + secrets.token_hex(32))
p.write_text("\n".join(out) + "\n")
PY
chmod 600 .env
mkdir -p .runtime
chmod 700 .runtime

say '[+] creating Neco Python environment'
python3 -m venv neco/.venv
neco/.venv/bin/python -m pip install --upgrade pip
neco/.venv/bin/pip install -r neco/requirements.txt

if [[ "$WITH_OLLAMA" == true ]]; then
  [[ -x scripts/setup-ollama.sh ]] || chmod +x scripts/setup-ollama.sh
  ./scripts/setup-ollama.sh
else
  say '[i] backend setup skipped; use Open WebUI Connections for any OpenAI-compatible backend.'
  say '[i] for the bundled local Ollama path: bash ./install.sh --ollama (or ./scripts/setup-ollama.sh later)'
fi

BASE_IMAGE="$(awk 'toupper($1) == "FROM" {print $2; exit}' openwebui/Dockerfile)"
[[ -n "$BASE_IMAGE" ]] || die 'No base image found in openwebui/Dockerfile.'
say "[+] pulling $BASE_IMAGE"
for attempt in 1 2 3; do
  if "${DOCKER[@]}" pull "$BASE_IMAGE"; then break; fi
  [[ "$attempt" == 3 ]] && die 'Open WebUI base image pull failed after 3 attempts.'
  sleep 5
done

say '[+] building the Den'
compose up -d --build

mkdir -p "$HOME/.config/systemd/user"
cat > "$HOME/.config/systemd/user/echo-local-ai-v2-neco.service" <<EOF
[Unit]
Description=Echo Local AI v2 - Neco
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=$ROOT
EnvironmentFile=$ROOT/.env
Environment=NECO_TOKEN_FILE=$ROOT/.runtime/neco_token
Environment=NECO_STATE_FILE=$ROOT/.runtime/neco_state.json
ExecStart=$ROOT/neco/.venv/bin/python -u -m neco.runtime
Restart=on-failure
RestartSec=10
TimeoutStopSec=15

[Install]
WantedBy=default.target
EOF
systemctl --user daemon-reload
systemctl --user stop echo-local-ai-v2-neco.service 2>/dev/null || true

BASE_URL="$(python3 -c 'from neco.config import Settings; print(Settings.from_env().base_url)')"

say '[+] waiting for the Den health endpoint'
ready=false
for _ in {1..90}; do
  if python3 - "$BASE_URL" <<'PY' >/dev/null 2>&1
import sys, urllib.request
with urllib.request.urlopen(sys.argv[1].rstrip("/") + "/health", timeout=2) as r:
    raise SystemExit(0 if r.status == 200 else 1)
PY
  then ready=true; break; fi
  sleep 2
done

if [[ "$ready" == true ]]; then
  say "[+] Den ready: $BASE_URL"
else
  say '[!] Den is still starting. First boot may download an embedding model.'
  say '    Check: sudo docker compose logs --tail=100 openwebui'
fi

echo
echo '========================================'
echo ' Echo Local AI v2 staged successfully'
echo '========================================'
echo "Open $BASE_URL"
echo '1. Create the first Open WebUI account (admin).'
echo '2. Connect/select a backend and verify NECO_MODEL can answer a normal chat.'
echo '3. Create an API key in Settings > Account > API keys.'
echo '4. Run: bash ./scripts/finish-setup.sh'
echo
echo 'The browser-auth/API-key step is the only intentionally manual boundary.'
