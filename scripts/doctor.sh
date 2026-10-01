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
import shutil
import subprocess
import sys
import urllib.error
import urllib.request

root = Path(sys.argv[1])
sys.path.insert(0, str(root))
from neco.config import Settings

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

try:
    settings = Settings.from_env(root)
    report(True, 'central config loads')
except (OSError, ValueError) as exc:
    report(False, 'central config loads', str(exc))
    raise SystemExit(1)

model = settings.model
base = settings.base_url.rstrip('/')
report(settings.persona_file.is_file(), 'persona file exists', str(settings.persona_file))

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
report(docker_ok, 'Docker daemon accessible', 'Run sudo -v, then rerun doctor; or fix Docker permissions.')

if docker_ok:
    ok, output = run(docker + ['inspect', '-f', '{{.State.Status}}', 'echo-local-ai-v2-webui'])
    report(ok and output == 'running', 'v2 Den container running', 'Run docker compose up -d --build.')
else:
    report(False, 'v2 Den container check unavailable', 'Fix Docker access first.')

opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
try:
    with opener.open(base + '/health', timeout=settings.api_timeout) as response:
        healthy = response.status == 200
    report(healthy, 'Den health endpoint ready', 'Inspect docker compose logs --tail=100 openwebui.')
except (OSError, ValueError, urllib.error.URLError):
    report(False, 'Den health endpoint ready', f'Cannot reach {base}/health. Check Open WebUI and the configured URL.')

try:
    token = settings.token_file.read_text(encoding='utf-8').strip()
except (OSError, UnicodeError):
    token = ''
report(bool(token), 'API key saved (contents hidden)', './scripts/set-token.sh')

if token:
    req = urllib.request.Request(base + '/api/models', headers={'Authorization': 'Bearer ' + token})
    try:
        with opener.open(req, timeout=settings.api_timeout) as response:
            data = json.load(response)
        models = {item.get('id') for item in data.get('data', [])}
        report(True, 'Open WebUI API key accepted')
        report(model in models, 'configured model visible in Open WebUI', 'Fix NECO_MODEL or the Open WebUI backend connection.')
    except urllib.error.HTTPError as exc:
        report(False, 'Open WebUI API key accepted', f'HTTP {exc.code}; create a fresh admin API key.')
    except (OSError, ValueError, KeyError, TypeError, urllib.error.URLError):
        report(False, 'Open WebUI model/API check', 'Open WebUI answered unexpectedly; inspect its logs/backend.')
else:
    report(False, 'Open WebUI model/API check', 'Save an API key first.')

for state in ('enabled', 'active'):
    ok, _ = run(['systemctl', '--user', '--no-pager', f'is-{state}', '--quiet', 'echo-local-ai-v2-neco.service'])
    report(ok, f'Neco v2 user service {state}', './scripts/start-neco.sh after finish-setup.')

if shutil.which('ollama'):
    ok, _ = run(['ollama', 'list'])
    print(f'[{"INFO" if ok else "WARN"}] Ollama is installed' + ('' if ok else ' but its CLI cannot reach the daemon'))
else:
    print('[INFO] Ollama not installed; that is fine when Open WebUI uses another compatible backend.')

ok, linger = run(['loginctl', '--no-pager', 'show-user', str(os.getuid()), '-p', 'Linger', '--value'])
report(ok and linger == 'yes', 'user linger enabled', 'finish-setup enables linger for the resident service.')

print(f'\n{failures} failed check(s).')
sys.exit(1 if failures else 0)
PY
