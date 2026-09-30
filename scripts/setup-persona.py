#!/usr/bin/env python3
"""Apply the shipped persona to the configured base model through Open WebUI's API."""
import json
from pathlib import Path
import shlex
import sys
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parent.parent


def main():
    settings = {}
    for line in (ROOT / '.env').read_text().splitlines():
        key, sep, value = line.partition('=')
        if sep and key.strip() in ('NECO_MODEL', 'OPENWEBUI_PORT', 'OPENWEBUI_URL', 'OWNER_NAME'):
            words = shlex.split(value, comments=True)
            settings[key.strip()] = words[0] if words else ''
    model = settings.get('NECO_MODEL', '').strip()
    if not model:
        raise ValueError('Set NECO_MODEL in .env first.')
    token = (ROOT / '.runtime/neco_token').read_text().strip()
    if not token:
        raise ValueError('Run ./scripts/set-token.sh with an admin API key first.')
    base = settings.get('OPENWEBUI_URL') or 'http://127.0.0.1:' + settings.get('OPENWEBUI_PORT', '3000')
    prompt = (ROOT / 'neco/persona.md').read_text().replace('Echo', settings.get('OWNER_NAME') or 'Echo')
    if not prompt.strip():
        raise ValueError('neco/persona.md is empty.')

    def api(path, payload=None):
        request = urllib.request.Request(base.rstrip('/') + path,
            data=json.dumps(payload).encode() if payload is not None else None,
            headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'})
        with urllib.request.urlopen(request, timeout=15) as response:
            return json.load(response)

    # Fail before mutation when the configured model is unavailable to this account.
    models = api('/api/models')
    if model not in {item['id'] for item in models.get('data', [])}:
        raise ValueError('NECO_MODEL is not available to this account. Check the Ollama connection and model name.')
    path = '/api/v1/models/model?id=' + urllib.parse.quote(model, safe='')
    try:
        existing = api(path)
    except urllib.error.HTTPError as error:
        if error.code != 404:
            raise
        existing = None
    if existing is not None and existing.get('write_access') is False:
        raise ValueError('This API key cannot edit the model. Use an admin key.')
    payload = {key: existing[key] for key in
        ('id', 'base_model_id', 'name', 'meta', 'params', 'access_grants', 'is_active')
        if existing and key in existing}
    if not existing:
        payload = dict(id=model, base_model_id=None, name='Neco', meta={}, params={}, is_active=True)
    payload['params'] = dict(payload.get('params') or {}, system=prompt)
    result = api('/api/v1/models/model/update' if existing else '/api/v1/models/create', payload)
    if not result:
        raise ValueError('Open WebUI did not confirm the model update.')
    saved = api(path)
    if not saved or saved.get('params', {}).get('system') != prompt:
        raise ValueError('Persona could not be verified after saving.')
    print('Neco personality saved and verified for ' + model + '.')
    print('Refresh the Den and start a new chat with this model (new entries are named Neco).')
    print('Your account Personalization field can remain empty; the model now supplies the system prompt.')


if __name__ == '__main__':
    try:
        main()
    except urllib.error.HTTPError as error:
        print(f'Persona setup failed: HTTP {error.code}. Check your admin API key and API endpoint permissions.', file=sys.stderr)
        sys.exit(1)
    except (OSError, ValueError, KeyError, TypeError) as error:
        # Never print API response bodies, authorization headers, or token contents.
        print('Persona setup failed. Check .env, neco/persona.md, the token file, and the Den connection.', file=sys.stderr)
        sys.exit(1)
