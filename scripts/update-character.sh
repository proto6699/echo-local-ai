#!/usr/bin/env bash
# Apply only Neco's identity/canon to an installed original or v2 Den.
set -euo pipefail
TARGET="$(cd "${1:-$PWD}" && pwd)"
[[ -f "$TARGET/.env" && -f "$TARGET/scripts/setup-persona.py" ]] || { echo 'Pass the functioning installation directory.' >&2; exit 1; }
SOURCE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEMP=""
if [[ ! -f "$SOURCE/neco/world/lore.json" ]]; then
  TEMP="$(mktemp -d)"
  trap 'rm -rf -- "$TEMP"' EXIT
  git clone --quiet --depth 1 https://github.com/proto6699/echo-local-ai.git "$TEMP/source"
  SOURCE="$TEMP/source"
fi
BACKUP="$TARGET/.runtime/character-backups/$(date +%Y%m%d-%H%M%S)-$$"
mkdir -p "$BACKUP/files"
chmod 700 "$BACKUP"
SERVICE=echo-local-ai-neco.service
[[ ! -f "$TARGET/neco/config.py" ]] || SERVICE=echo-local-ai-v2-neco.service
was_active=false
if systemctl --user is-active --quiet "$SERVICE"; then
  WORKDIR="$(systemctl --user show "$SERVICE" --property=WorkingDirectory --value)"
  [[ "$WORKDIR" == "$TARGET/neco" || "$WORKDIR" == "$TARGET" ]] || { echo 'Running service belongs to another directory; no changes made.' >&2; exit 1; }
  was_active=true
fi
FILES=(neco/persona-lite.md neco/persona.md)
if [[ -d "$TARGET/neco/world" ]]; then
  FILES+=(neco/world/identity.md neco/world/lore.json neco/world/arcs.json neco/world/WORLD_BIBLE.md)
fi
# v2 already loads its identity through config.py; retain its daemon code.
if [[ ! -f "$TARGET/neco/config.py" ]]; then FILES+=(neco/runtime.py neco/neco_monologue.py); fi
: > "$BACKUP/added-files.txt"
: > "$BACKUP/replaced-files.txt"
for relative in "${FILES[@]}" .env; do
  if [[ -f "$TARGET/$relative" ]]; then
    mkdir -p "$BACKUP/files/$(dirname "$relative")"
    cp -p -- "$TARGET/$relative" "$BACKUP/files/$relative"
    printf '%s\n' "$relative" >> "$BACKUP/replaced-files.txt"
  else printf '%s\n' "$relative" >> "$BACKUP/added-files.txt"; fi
done
printf '%s\n' "$SERVICE" > "$BACKUP/service.txt"
printf '%s\n' "$was_active" > "$BACKUP/was-active.txt"
trap 'echo "Character update stopped. Backup: $BACKUP" >&2' ERR
if [[ "$was_active" == true ]]; then systemctl --user stop "$SERVICE"; fi
for relative in "${FILES[@]}"; do
  mkdir -p "$TARGET/$(dirname "$relative")"
  cp -p -- "$SOURCE/$relative" "$TARGET/$relative"
done
python3 - "$TARGET" "$BACKUP" <<'PY'
import sys
from pathlib import Path
root, backup = map(Path, sys.argv[1:])
env = root / '.env'
lines = env.read_text().splitlines()
title = 'NECO_CHAT_TITLE="Neco — idle (continuity)"'
found = False
for index, line in enumerate(lines):
    if line.startswith('NECO_CHAT_TITLE='):
        lines[index] = title
        found = True
if not found: lines.append(title)
env.write_text('\n'.join(lines) + '\n')
env.chmod(0o600)
state = root / '.runtime/neco-presence.json'
if state.exists():
    state.rename(backup / 'neco-presence.json')
PY
PYTHON=python3
[[ ! -x "$TARGET/neco/.venv/bin/python" ]] || PYTHON="$TARGET/neco/.venv/bin/python"
"$PYTHON" "$TARGET/scripts/setup-persona.py"
if [[ "$was_active" == true ]]; then systemctl --user start "$SERVICE"; fi
echo "Character applied. Backup: $BACKUP"
echo 'Start a NEW Neco chat. Previous idle chats and memories are retained.'
echo 'If the daemon was stopped, start it with ./scripts/start-neco.sh.'
