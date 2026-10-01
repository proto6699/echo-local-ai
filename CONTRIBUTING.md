# contributing to Echo Local AI v2

The project is intentionally small. The best contributions make the resident more reliable without turning it into a framework.

## before opening a PR

Run:

```bash
python -m pip install -r neco/requirements.txt -r neco/requirements-dev.txt
pytest -q
ruff check neco tests
```

For runtime/API changes, also run:

```bash
bash ./scripts/test-neco.sh
bash ./scripts/doctor.sh
```

## boundaries worth keeping

- local-first by default
- no arbitrary shell/tool execution from Neco chat
- host telemetry remains read-only and best-effort
- Open WebUI persistence internals stay isolated in `neco/chat.py`
- all runtime configuration comes through `Settings` / `.env`
- backend-specific setup belongs in helpers/docs, not the core daemon
- personality is presentation; technical errors should still be concrete and useful

## changes that need extra care

Open WebUI internal chat endpoints can change between releases. If you touch `neco/chat.py`, describe the Open WebUI version you tested and the exact API behavior relied on.

Sensor code must fail closed: missing hardware support should produce `None`, not invented values and not a dead daemon.

Do not commit API keys, `.env`, `.runtime/`, model files, or personal chat data.

## PR shape

Keep the diff focused. Include a test for pure logic when practical. If a change needs new configuration, update `.env.example` and the README config table in the same PR.
