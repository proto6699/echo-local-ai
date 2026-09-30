#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

die() { echo "error: $*" >&2; exit 1; }

command -v docker >/dev/null 2>&1 || die "Docker is not installed."
docker compose version >/dev/null 2>&1 || die "Docker Compose plugin is missing."
command -v python3 >/dev/null 2>&1 || die "Python 3 is not installed."
command -v systemctl >/dev/null 2>&1 || die "systemd/systemctl is required."

[[ -f neco/neco_monologue.py ]] || die "Missing Neco."
[[ -f openwebui/overlay/index.html ]] || die "Missing Den UI."

if [[ ! -f .env ]]; then
  cp .env.example .env
fi

python3 - .env <<'PY'
from pathlib import Path
import secrets, sys
p = Path(sys.argv[1])
lines = p.read_text().splitlines()
out, found = [], False
for line in lines:
    if line.startswith("WEBUI_SECRET_KEY="):
        found = True
        if not line.split("=",1)[1].strip():
            line = "WEBUI_SECRET_KEY=" + secrets.token_hex(32)
    out.append(line)
if not found:
    out.append("WEBUI_SECRET_KEY=" + secrets.token_hex(32))
p.write_text("\n".join(out) + "\n")
PY

chmod 600 .env
mkdir -p .runtime
chmod 700 .runtime

python3 -m venv neco/.venv
neco/.venv/bin/python -m pip install --upgrade pip
neco/.venv/bin/pip install -r neco/requirements.txt

docker compose up -d --build

mkdir -p "$HOME/.config/systemd/user"

cat > "$HOME/.config/systemd/user/echo-local-ai-neco.service" <<EOF
[Unit]
Description=Echo Local AI - Neco
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=$ROOT/neco
EnvironmentFile=$ROOT/.env
Environment=NECO_TOKEN_FILE=$ROOT/.runtime/neco_token
Environment=NECO_STATE_FILE=$ROOT/.runtime/neco_state.json
ExecStart=$ROOT/neco/.venv/bin/python -u $ROOT/neco/runtime.py
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user stop echo-local-ai-neco.service 2>/dev/null || true

echo
echo "Den started."
echo "Next: configure Open WebUI, create an API key, then run:"
echo "  ./scripts/set-token.sh"
echo "  ./scripts/test-neco.sh"
echo "  ./scripts/start-neco.sh"
