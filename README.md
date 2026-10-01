# Echo Local AI v2

> **not an assistant. a resident process with opinions.**

Echo Local AI is a local-first experiment in giving a small local model a place to *live* instead of another chat box to wait inside.

**The Den** is a CRT-styled Open WebUI. **Neco** is the resident. A tiny systemd user service keeps running after the browser closes, occasionally drops an unsolicited thought into **Neco — idle**, and samples a few read-only host vitals when the conversation actually needs them.

No agent swarm. No cloud requirement. No claim that the gremlin is conscious. Just a deliberately persistent local character with questionable timing.

![The Den](docs/screenshots/den-home.png)

## what changed in v2

v1 proved the idea. v2 cleans up the machinery underneath it.

- one config source: `.env` → `neco.config.Settings`
- the old ~480-line monolith is gone
- runtime split into `client`, `chat`, `generation`, `reactive`, `loop`, and `system_vitals`
- streamed completions by default, with SIGINT/SIGTERM cancellation
- retries + exponential backoff for temporary Open WebUI failures
- useful errors for dead Open WebUI, invalid tokens, missing models, and bad config
- recent idle context is actually supplied to generation instead of being calculated and ignored
- exact dependency pins, unit tests, Ruff, and GitHub Actions
- backend-agnostic daemon: Ollama is convenient, not mandatory
- v2 service/container names can coexist with a v1 checkout while you test

The one awkward setup boundary remains intentional: Open WebUI's first account and API key must be created by you in the browser.

## the stack

```text
local model backend
  ollama / lm studio / llama.cpp / vllm / other OpenAI-compatible source
                          │
                          ▼
                 Open WebUI + Den overlay
                          │
             ┌────────────┴────────────┐
             ▼                         ▼
        normal chat              Neco v2 daemon
                                 systemd --user
                                     │
                        ┌────────────┴────────────┐
                        ▼                         ▼
                 idle thoughts          read-only vitals snapshot
                        │                         │
                        └────────────┬────────────┘
                                     ▼
                              Neco — idle
```

## bring the gremlin home

Requirements: **Linux + systemd + Git**. The installer can add Docker/Compose/Python on Arch-family and Debian-family systems.

### quickest local Ollama path

```bash
git clone https://github.com/proto6699/echo-local-ai-v2.git
cd echo-local-ai-v2
bash ./install.sh --ollama
```

`--ollama` is optional. Without it, the installer brings up the Den and you can configure any supported Open WebUI connection yourself.

Then open **http://localhost:3000**:

1. create the first Open WebUI account
2. make sure the model named by `NECO_MODEL` can answer a normal message
3. create an API key under **Settings → Account → API keys**
4. finish the resident setup:

```bash
bash ./scripts/finish-setup.sh
```

That command saves the key locally, applies Neco's persona/avatar/filter, posts one test thought, enables the user service, and runs diagnostics.

## what keeps running?

Closing Safari/Firefox/Chromium does **not** stop Neco. The daemon is a systemd **user** service:

```bash
systemctl --user status echo-local-ai-v2-neco.service
```

Stop unsolicited thoughts:

```bash
systemctl --user stop echo-local-ai-v2-neco.service
```

Bring her back:

```bash
bash ./scripts/start-neco.sh
```

A clean systemd stop sets a cancellation event, closes an active streaming response, and exits instead of waiting on a long generation timeout.

## config

Everything the runtime consumes comes from `.env`.

| setting | default | job |
| --- | --- | --- |
| `NECO_MODEL` | `llama3.2:1b` | exact model ID visible in Open WebUI |
| `NECO_PERSONA` | `lite` | `lite` or `full` persona |
| `NECO_MIN_INTERVAL` | `1200` | minimum seconds between idle thoughts |
| `NECO_MAX_INTERVAL` | `2700` | maximum seconds between idle thoughts |
| `NECO_STREAM` | `true` | stream model output to the daemon |
| `NECO_MAX_CONTEXT_MESSAGES` | `8` | recent idle messages supplied to generation |
| `NECO_RETRY_ATTEMPTS` | `4` | temporary HTTP retry count |
| `NECO_RETRY_BASE_SECONDS` | `2` | exponential retry base delay |
| `NECO_GENERATION_TIMEOUT` | `180` | model read timeout |
| `NECO_VITALS_INTERVAL` | `5` | host-vitals snapshot interval |
| `OWNER_NAME` | `Echo` | name used by the persona |
| `NECO_MACHINE` | `this machine` | machine wording used by the persona |

After changing model/persona settings, rerun:

```bash
python3 scripts/setup-persona.py
systemctl --user restart echo-local-ai-v2-neco.service
```

## model backends

The daemon talks to **Open WebUI**, not directly to Ollama. If Open WebUI can expose the model under `NECO_MODEL`, Neco can use it.

### Ollama

```bash
bash ./scripts/setup-ollama.sh
```

The helper binds Ollama to `0.0.0.0:11434` because Docker needs to reach the host service. **Do not expose port 11434 to untrusted LAN/WAN clients.** Firewall it to trusted traffic/Docker.

### LM Studio / llama.cpp / vLLM / other OpenAI-compatible servers

Add the server in Open WebUI **Connections**, verify a normal chat, then set `NECO_MODEL` to the model ID Open WebUI shows. You do not need to modify the daemon.

## experimental system vitals

The host runtime writes a small snapshot to `.runtime/system-vitals.json`. The Den mounts **only that runtime directory read-only**. The Neco filter injects the snapshot only for questions about system health, temperature, load, memory, uptime, or similar signals.

Current best-effort sensors:

- uptime + 1/5/15 minute load
- RAM used / total
- CPU temperature when Linux exposes a usable sensor
- AMD GPU load, temperature, and VRAM when available via sysfs

Raw reading:

```bash
python3 -m neco.system_vitals
```

No shell execution from chat. No privileged container. No write controls. She can feel the fever; she still cannot touch the thermostat.

## under the floorboards

```text
neco/
├── config.py          single validated runtime config
├── client.py          Open WebUI HTTP + streaming + retry policy
├── chat.py            Open WebUI saved-chat internals live here only
├── generation.py      idle prompt construction + generation
├── reactive.py        deterministic/reactive host observations
├── loop.py            lifecycle, cancellation, vitals thread
├── runtime.py         tiny CLI entry point
└── system_vitals.py   read-only telemetry collection
```

Open WebUI's private chat-history shape is still an upstream coupling. v2 deliberately isolates that coupling inside `neco/chat.py` so an upstream break should require one repair instead of archaeology through the whole daemon.

## maintenance hatch

```bash
# read-only diagnostics
bash ./scripts/doctor.sh

# one live thought then exit
bash ./scripts/test-neco.sh

# logs
journalctl --user -u echo-local-ai-v2-neco.service -f

# Den container
sudo docker compose ps
sudo docker compose logs --tail=100 openwebui

# tests
python -m pip install -r neco/requirements.txt -r neco/requirements-dev.txt
pytest -q
ruff check neco tests
```

## roadmap

The architectural cleanup is the v2 milestone. Next sensible work is intentionally smaller: harden Open WebUI compatibility tests, add NVIDIA/Intel GPU vitals, make first-run browser auth less awkward where upstream APIs permit it, and add a tiny optional localhost health endpoint for the daemon.

No plans for autonomous tool use, arbitrary host control, multi-agent cosplay, or turning this into a production platform. That would be a different project wearing Neco's coat.

## contributing

Small focused fixes are welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md) before teaching the gremlin new tricks.

## credits

Built on **Open WebUI**, VT323, and the existing Den/Neco assets. Original project code is MIT-licensed. Bundled upstream software, fonts, images, and music retain their own licenses; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) and [OPENWEBUI_LICENSE.txt](OPENWEBUI_LICENSE.txt).

> serious engineering, playful presentation.
