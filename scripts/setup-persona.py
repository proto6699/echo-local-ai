#!/usr/bin/env python3
"""Apply the shipped persona to the configured base model through Open WebUI's API."""
import base64
import json
from pathlib import Path
import shlex
import sys
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parent.parent


class SetupError(Exception):
    """A safe, actionable message constructed by this script."""


def step(message):
    print('[setup] ' + message, flush=True)


def main():
    step("Reading .env")
    settings = {}
    for line in (ROOT / '.env').read_text().splitlines():
        key, sep, value = line.partition('=')
        if sep and key.strip() in ('NECO_MODEL', 'OPENWEBUI_PORT', 'OPENWEBUI_URL', 'OWNER_NAME'):
            words = shlex.split(value, comments=True)
            settings[key.strip()] = words[0] if words else ''
    model = settings.get('NECO_MODEL', '').strip()
    if not model:
        raise SetupError('Set NECO_MODEL in .env first.')
    step('Reading saved API key (contents hidden)')
    token = (ROOT / '.runtime/neco_token').read_text().strip()
    if not token:
        raise SetupError('Run ./scripts/set-token.sh with an admin API key first.')
    base = settings.get('OPENWEBUI_URL') or 'http://127.0.0.1:' + settings.get('OPENWEBUI_PORT', '3000')
    step('Reading neco/persona.md')
    prompt = (ROOT / 'neco/persona.md').read_text().replace('Echo', settings.get('OWNER_NAME') or 'Echo')
    if not prompt.strip():
        raise SetupError('neco/persona.md is empty.')

    def api(path, payload=None):
        request = urllib.request.Request(base.rstrip('/') + path,
            data=json.dumps(payload).encode() if payload is not None else None,
            headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'})
        with urllib.request.urlopen(request, timeout=15) as response:
            return json.load(response)

    # Fail before mutation when the configured model is unavailable to this account.
    step('Checking models visible to the Open WebUI account')
    models = api('/api/models')
    if model not in {item['id'] for item in models.get('data', [])}:
        raise SetupError('NECO_MODEL is not available to this account. Check the Ollama connection and model name.')
    path = '/api/v1/models/model?id=' + urllib.parse.quote(model, safe='')
    step('Reading existing model configuration')
    try:
        existing = api(path)
    except urllib.error.HTTPError as error:
        if error.code != 404:
            raise
        existing = None
    if existing is not None and existing.get('write_access') is False:
        raise SetupError('This API key cannot edit the model. Use an admin key.')
    payload = {key: existing[key] for key in
        ('id', 'base_model_id', 'name', 'meta', 'params', 'access_grants', 'is_active')
        if existing and key in existing}
    if not existing:
        payload = dict(id=model, base_model_id=None, name='Neco', meta={}, params={}, is_active=True)
    payload['params'] = dict(payload.get('params') or {}, system=prompt)
    # OWUI rejects arbitrary relative profile URLs; embedded PNGs are supported.
    step('Reading bundled Neco avatar')
    image = (ROOT / 'openwebui/overlay/static/den-neco.png').read_bytes()
    if not image.startswith(b'\x89PNG\r\n\x1a\n'):
        raise SetupError('The bundled Neco avatar is not a PNG. Restore den-neco.png from the repo.')
    avatar = 'data:image/png;base64,' + base64.b64encode(image).decode('ascii')
    payload['meta'] = dict(payload.get('meta') or {}, profile_image_url=avatar)
    step('Saving personality and avatar')
    result = api('/api/v1/models/model/update' if existing else '/api/v1/models/create', payload)
    if not result:
        raise SetupError('Open WebUI did not confirm the model update.')
    step('Verifying saved personality and avatar')
    saved = api(path)
    if not saved or saved.get('params', {}).get('system') != prompt:
        raise SetupError('Persona could not be verified after saving.')
    if saved.get('meta', {}).get('profile_image_url') != payload['meta']['profile_image_url']:
        raise SetupError('Neco avatar could not be verified after saving.')
    print('Neco personality and avatar saved and verified for ' + model + '.')
    print('Refresh the Den and start a new chat with this model (new entries are named Neco).')
    print('Your account Personalization field can remain empty; the model now supplies the system prompt.')


if __name__ == '__main__':
    try:
        main()
    except urllib.error.HTTPError as error:
        print(f'Persona setup failed: HTTP {error.code}. Check your admin API key and API endpoint permissions.', file=sys.stderr)
        sys.exit(1)
    except SetupError as error:
        print('Persona setup failed: ' + str(error), file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError as error:
        name = Path(error.filename).name if error.filename else 'required file'
        hint = 'Run ./scripts/set-token.sh.' if name == 'neco_token' else 'Run ./install.sh or restore the missing repo file.'
        print(f'Persona setup failed: missing {name}. {hint}', file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError:
        print('Persona setup failed: cannot reach Open WebUI. Check the container, OPENWEBUI_PORT/OPENWEBUI_URL, and /health.', file=sys.stderr)
        sys.exit(1)
    except TimeoutError:
        print('Persona setup failed: Open WebUI request timed out. Wait for first boot to finish, then retry.', file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError:
        print('Persona setup failed: Open WebUI returned a non-JSON response. Check its URL/port and container logs.', file=sys.stderr)
        sys.exit(1)
    except PermissionError:
        print('Persona setup failed: a required file is not readable. Run as the user who installed the project.', file=sys.stderr)
        sys.exit(1)
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        # Never print response bodies, authorization headers, or token contents.
        print(f'Persona setup failed: {type(error).__name__} at the step above. Check .env syntax and the Open WebUI API response format.', file=sys.stderr)
        sys.exit(1)
