#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

die() {
    echo "error: $*" >&2
    exit 1
}

say() {
    echo "$*"
}

install_host_deps() {
    # Already good? Don't touch the package manager.
    if command -v docker >/dev/null 2>&1        && (docker compose version >/dev/null 2>&1 || command -v docker-compose >/dev/null 2>&1)        && command -v python3 >/dev/null 2>&1        && python3 -m venv --help >/dev/null 2>&1; then
        return
    fi

    [[ -r /etc/os-release ]] || die "Can't identify this Linux distribution."
    # shellcheck disable=SC1091
    source /etc/os-release

    local family="${ID:-} ${ID_LIKE:-}"

    echo
    echo "some host dependencies are missing."
    printf "install Docker / Compose / Python bits now? [Y/n] "
    read -r answer
    answer="${answer:-Y}"

    case "$answer" in
        y|Y|yes|YES) ;;
        *) die "Install cancelled." ;;
    esac

    if [[ "$family" == *"arch"* ]]; then
        sudo pacman -S --needed --noconfirm docker docker-compose python
    elif [[ "$family" == *"ubuntu"* ]]; then
        sudo apt-get update
        sudo apt-get install -y docker.io docker-compose-v2 python3 python3-venv
    elif [[ "$family" == *"debian"* ]]; then
        sudo apt-get update
        # Debian versions differ on the Compose package name.
        if ! sudo apt-get install -y docker.io docker-compose-v2 python3 python3-venv; then
            sudo apt-get install -y docker.io docker-compose python3 python3-venv
        fi
    else
        die "Automatic dependency install currently supports Arch/CachyOS/EndeavourOS and Debian/Ubuntu. Install Docker, Compose, Python 3 + venv, then rerun ./install.sh."
    fi
}

install_host_deps

command -v docker >/dev/null 2>&1 || die "Docker is still unavailable."
command -v python3 >/dev/null 2>&1 || die "Python 3 is still unavailable."
command -v systemctl >/dev/null 2>&1 || die "systemd/systemctl is required."

RUNNING_KERNEL="$(uname -r)"
if [[ ! -d "/lib/modules/$RUNNING_KERNEL" ]]; then
    echo
    echo "kernel/module mismatch detected."
    echo "running kernel:  $RUNNING_KERNEL"
    echo "modules for that kernel are missing from /lib/modules."
    echo
    die "The kernel was probably upgraded while this system was still running. Reboot, then rerun ./install.sh."
fi

[[ -f neco/neco_monologue.py ]] || die "Missing Neco."
[[ -f openwebui/overlay/index.html ]] || die "Missing Den UI."

# Docker's daemon may exist but not be running yet.
if ! sudo systemctl is-active --quiet docker; then
    say "[+] starting Docker"
    sudo systemctl reset-failed docker 2>/dev/null || true

    if ! sudo systemctl enable --now docker; then
        echo
        echo "Docker failed to start. Recent daemon errors:"
        echo "---------------------------------------------"
        sudo journalctl -u docker.service -n 80 --no-pager 2>/dev/null \
            | grep -Ei 'error|failed|fatal|daemon|iptables|nft|overlay|bridge|network' \
            | tail -40 || true
        echo "---------------------------------------------"
        echo
        die "Docker daemon failed to start. The log above contains the real cause."
    fi
fi

# Use Docker directly when the current user already has permission.
# Otherwise use sudo for this installation instead of forcing a logout/login.
if docker info >/dev/null 2>&1; then
    DOCKER=(docker)
else
    DOCKER=(sudo docker)
    say "[i] using sudo for Docker during this install"
    say "[i] optional later: sudo usermod -aG docker \$USER  (then log out/in)"
fi

if "${DOCKER[@]}" compose version >/dev/null 2>&1; then
    compose() {
        "${DOCKER[@]}" compose "$@"
    }
elif command -v docker-compose >/dev/null 2>&1; then
    if [[ "${DOCKER[0]}" == "sudo" ]]; then
        compose() {
            sudo docker-compose "$@"
        }
    else
        compose() {
            docker-compose "$@"
        }
    fi
else
    die "Docker Compose is still unavailable."
fi

if [[ ! -f .env ]]; then
    cp .env.example .env
    say "[+] created .env"
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

say "[+] creating Neco Python environment"
python3 -m venv neco/.venv
neco/.venv/bin/python -m pip install --upgrade pip
neco/.venv/bin/pip install -r neco/requirements.txt

say "[+] building the Den"
compose up -d --build

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

PORT="$(python3 - .env <<'PY'
from pathlib import Path
port = "3000"
for line in Path(".env").read_text().splitlines():
    if line.startswith("OPENWEBUI_PORT="):
        port = line.split("=", 1)[1].strip().strip('"').strip("'") or "3000"
print(port)
PY
)"

echo
echo "========================================"
echo " the Den is up"
echo "========================================"
echo
echo "open:"
echo "  http://localhost:$PORT"
echo
echo "then:"
echo "  1. create your Open WebUI account"
echo "  2. configure a model and verify normal chat works"
echo "  3. create an Open WebUI API key"
echo "  4. ./scripts/set-token.sh"
echo "  5. ./scripts/test-neco.sh"
echo "  6. ./scripts/start-neco.sh"
echo
echo "Neco has not been started yet."
