# setup + troubleshooting notes — v2

## no model appears in the Den

The v2 daemon is backend-agnostic. Fix the model in Open WebUI first, then Neco.

For Ollama, verify the host:

```bash
OLLAMA_HOST=127.0.0.1:11434 ollama list
curl -sS -m 5 http://127.0.0.1:11434/api/tags
```

Open WebUI should point to:

```text
http://host.docker.internal:11434
```

For LM Studio / llama.cpp / vLLM / another OpenAI-compatible source, configure it in **Open WebUI → Connections** and verify a normal chat. Then set `NECO_MODEL` to the exact model ID Open WebUI exposes.

## Ollama + Docker security

`scripts/setup-ollama.sh` binds Ollama to `0.0.0.0:11434` because a bridged Docker container cannot reach a host service bound only to host loopback. Ollama's local API is not intended to be exposed casually.

Keep TCP **11434** blocked from untrusted LAN/WAN clients. The Den itself stays on `127.0.0.1` unless you deliberately change `OPENWEBUI_BIND`.

## first boot looks unhealthy

Open WebUI may download an embedding model on first boot. Check:

```bash
sudo docker compose logs --tail=100 openwebui
curl -sS -m 5 http://localhost:3000/health
```

The v2 installer waits for health for roughly three minutes, then prints a warning instead of pretending startup succeeded.

## API key rejected

Create a fresh key from the admin account, then:

```bash
bash ./scripts/set-token.sh
python3 scripts/setup-persona.py
```

The daemon does not retry 401/403 responses because a bad credential will not heal with backoff.

## Open WebUI is temporarily down

The v2 client retries connection errors, timeouts, HTTP 429, and 5xx responses using bounded exponential backoff. After the retry budget is exhausted, the daemon logs one actionable error and waits `NECO_ERROR_INTERVAL` before trying again.

## daemon won't stop quickly

Generation streams by default. SIGINT/SIGTERM sets the runtime cancellation event and closes the active HTTP response. Check that `NECO_STREAM=true` and inspect:

```bash
journalctl --user -u echo-local-ai-v2-neco.service -n 100 --no-pager
```

## service survives browser close but not suspend

Expected. The systemd user service keeps running with the browser closed. Suspending the machine suspends the process too.

```bash
loginctl enable-linger "$USER"
bash ./scripts/start-neco.sh
```

## Docker permission denied

Use `sudo docker compose ...` for manual checks, or add your user to the Docker group and log out/in. Do **not** run the whole project installer as root.

## upstream Open WebUI breaks idle chat mutation

The saved-chat internals are the least stable integration point. v2 isolates them in `neco/chat.py`. If an Open WebUI upgrade changes those private endpoints/data shapes, start there instead of changing the generation/runtime code.
