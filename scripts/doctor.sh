#!/usr/bin/env bash
# Read-only diagnostics for Echo Local AI v2.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
command -v python3 >/dev/null || { echo '[FAIL] Python 3 is required.'; exit 1; }

exec python3 - "$ROOT" <<'PY'
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import urllib.error
import urllib.request

root = Path(sys.argv[1])
failures = 0


def report(ok, label, hint=''):
    global failures
    print(f'[{"PASS" if ok else "FAIL"}] {label}', flush=True)
    if not ok:
        failures += 1
        if hint:
            print(f'       {hint}', flush=True)


def run(args, timeout=10):
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False)
        return p.returncode == 0, p.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return False, ''


settings = {}
try:
    for line in (root / '.env').read_text().splitlines():
        key, sep, value = line.partition('=')
        if not sep:
            continue
        key = key.strip()
        if key in {'NECO_MODEL', 'OPENWEBUI_PORT', 'OPENWEBUI_URL'}:
            words = shlex.split(value, comments=True)
            settings[key] = words[0] if words else ''
    env_ok = True
except (OSError, ValueError):
    env_ok = False
report(env_ok, '.env readable', 'Run ./install.sh and check .env quoting.')

model = settings.get('NECO_MODEL', '')
port = settings.get('OPENWEBUI_PORT', '3000') or '3000'
base = settings.get('OPENWEBUI_URL') or f'http://127.0.0.1:{port}'
report(bool(model), 'NECO_MODEL configured', 'Set NECO_MODEL to a model visible in Open WebUI.')

ok, _ = run(['systemctl', '--no-pager', 'is-active', '--quiet', 'docker'])
report(ok, 'Docker service active', 'sudo systemctl enable --now docker')

docker = ['docker']
docker_ok, _ = run(docker + ['info'])
if not docker_ok and shutil.which('sudo'):
    try:
        cached = subprocess.run(['sudo', '-n', '-v'], timeout=3, check=False).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        cached = False
    if cached:
        docker = ['sudo', '-n', 'docker']
        docker_ok, _ = run(docker + ['info'])
report(docker_ok, 'Docker daemon accessible', 'Run sudo -v, then rerun doctor; or add your user to the docker group.')

if docker_ok:
    ok, output = run(docker + ['inspect', '-f', '{{.State.Status}}', 'echo-local-ai-v2-webui'])
    report(ok and output == 'running', 'v2 Den container running', 'Run docker compose up -d --build.')
else:
    report(False, 'v2 Den container check unavailable', 'Fix Docker access first.')

opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
try:
    with opener.open(base.rstrip('/') + '/health', timeout=5) as response:
        healthy = response.status == 200
    report(healthy, 'Den health endpoint ready', 'Inspect docker compose logs --tail=100 openwebui.')
except (OSError, ValueError, urllib.error.URLError):
    report(False, 'Den health endpoint ready', f'Cannot reach {base}/health. Check OPENWEBUI_URL/PORT and first-boot logs.')

try:
    token = (root / '.runtime/neco_token').read_text().strip()
except (OSError, UnicodeError):
    token = ''
report(bool(token), 'API key saved (contents hidden)', './scripts/set-token.sh')

if token:
    req = urllib.request.Request(base.rstrip('/') + '/api/models', headers={'Authorization': 'Bearer ' + token})
    try:
        with opener.open(req, timeout=8) as response:
            data = json.load(response)
        models = {item.get('id') for item in data.get('data', [])}
        report(True, 'Open WebUI API key accepted')
        report(model in models, 'configured model visible in Open WebUI', 'Fix NECO_MODEL or the Open WebUI backend connection.')
    except urllib.error.HTTPError as exc:
        report(False, 'Open WebUI API key accepted', f'HTTP {exc.code}; create a fresh admin API key and run ./scripts/set-token.sh.')
    except (OSError, ValueError, KeyError, TypeError, urllib.error.URLError):
        report(False, 'Open WebUI model/API check', 'Open WebUI answered unexpectedly; inspect its logs and backend connection.')
else:
    report(False, 'Open WebUI model/API check', 'Save an API key first.')

for state in ('enabled', 'active'):
    ok, _ = run(['systemctl', '--user', '--no-pager', f'is-{state}', '--quiet', 'echo-local-ai-v2-neco.service'])
    report(ok, f'Neco v2 user service {state}', './scripts/start-neco.sh after finish-setup.')

if shutil.which('ollama'):
    ok, _ = run(['ollama', 'list'])
    print(f'[{"INFO" if ok else "WARN"}] Ollama is installed' + ('' if ok else ' but its CLI cannot reach the configured daemon'))
else:
    print('[INFO] Ollama not installed; that is fine when Open WebUI uses another compatible backend.')

print(f'\n{failures} failed check(s).')
sys.exit(1 if failures else 0)
PY
