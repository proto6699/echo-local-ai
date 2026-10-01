# Echo Local AI v2

> **Not an assistant. A resident process with opinions.**

Echo Local AI is a local-first experiment in persistent AI presence. **The Den** is a CRT-styled Open WebUI. **Neco** is the resident. Close the browser and a small systemd user service can still wake up occasionally, generate an idle thought, and leave it in `Neco — idle` for later.

![The Den home screen with Neco, CRT typography, and music control](docs/screenshots/den-home.png)

**v2 keeps the weird part and replaces the plumbing.**

## Why v2 exists

The first version proved the idea, but the daemon had grown into one large file with old model/URL/token-path defaults, duplicate persona text, weak failure handling, and setup scripts that assumed Ollama everywhere.

v2 fixes that without turning the project into a framework:

- one config source: `.env` → `neco/config.py`
- no hidden model, URL, owner, machine, or token-path defaults elsewhere
- persona files are also the idle-thought persona source of truth
- daemon split into `client`, `chat`, `generation`, `reactive`, `system_vitals`, and `loop`
- streamed idle completions by default, with SIGINT/systemd cancellation
- retry/backoff and useful errors for downtime, invalid API keys, and API drift
- pinned dependencies, unit tests, Ruff, and GitHub Actions
- backend-agnostic runtime: Ollama is convenient, not mandatory
- v2-specific service/container names so it can coexist with v1 while you migrate

## Architecture

```text
Linux host
├─ model backend
│  └─ Ollama / LM Studio / llama.cpp / vLLM / other OpenAI-compatible backend
├─ Docker
│  └─ Open WebUI + Den overlay
│     └─ Neco system-vitals filter (read-only snapshot)
└─ systemd --user
   └─ Neco resident
      ├─ idle loop
      ├─ Open WebUI API client
      ├─ persisted idle-chat adapter
      ├─ thought generator
      └─ lightweight host observations
```

The resident talks to **Open WebUI**, not directly to Ollama. If Open WebUI can see the model, Neco can use it.

## Quickstart

Linux with systemd is required. Run scripts as your normal user; they request sudo only where host services need it.

While v2 is staged on the original repository branch:

```bash
git clone --branch v2 --single-branch https://github.com/proto6699/echo-local-ai.git echo-local-ai-v2
cd echo-local-ai-v2
./install.sh
```

If you use host Ollama and want the installer to configure/pull it too:

```bash
./install.sh --ollama
```

The installer builds the Den and waits for `/health`. Then open the printed URL, create the first Open WebUI account, connect a backend, verify `NECO_MODEL` answers a normal chat, and create an API key under **Settings → Account → API keys**.

Finish once:

```bash
./scripts/finish-setup.sh
```

That stores the key with mode `600`, applies Neco's persona/avatar/vitals filter, posts one test thought, enables user linger, and starts `echo-local-ai-v2-neco.service`.

The account/API-key step stays manual on purpose. Everything around it is scripted.

> Running v1 at the same time? It probably owns port `3000`. Set `OPENWEBUI_PORT=3001` in v2's `.env` before `docker compose up -d --build`.

## Configuration

Runtime settings live in `.env` and are loaded by `neco/config.py`.

| Setting | Default | Meaning |
| --- | --- | --- |
| `NECO_MODEL` | `llama3.2:1b` | Exact model ID visible in Open WebUI |
| `NECO_PERSONA` | `lite` | `lite` or `full` shipped persona |
| `OWNER_NAME` | `Echo` | Name used by the character |
| `NECO_MACHINE` | `this machine` | Machine wording substituted into persona lore |
| `NECO_MIN_INTERVAL` | `1200` | Minimum idle interval, seconds |
| `NECO_MAX_INTERVAL` | `2700` | Maximum idle interval, seconds |
| `NECO_ERROR_INTERVAL` | `60` | Delay after a failed idle cycle |
| `NECO_MAX_CONTEXT_MESSAGES` | `8` | Recent idle messages kept as generation context |
| `NECO_STREAM` | `true` | Stream idle generations |
| `NECO_API_TIMEOUT` | `15` | Ordinary Open WebUI timeout |
| `NECO_GENERATION_TIMEOUT` | `180` | Generation read timeout |
| `NECO_RETRY_ATTEMPTS` | `4` | Attempts for transient connection/5xx/429 failures |
| `NECO_RETRY_BASE_SECONDS` | `2` | Exponential backoff base |
| `NECO_VITALS_INTERVAL` | `5` | Host-vitals sampling interval |

After changing model/persona configuration:

```bash
python3 scripts/setup-persona.py
systemctl --user restart echo-local-ai-v2-neco.service
```

## Backends

### Ollama

`./scripts/setup-ollama.sh` configures host Ollama for Docker and pulls `NECO_MODEL`. It binds port `11434` on all interfaces so the container can reach the host; keep that port blocked from untrusted networks with your firewall.

### LM Studio, llama.cpp, vLLM, etc.

Add the server as an Open WebUI connection, verify its model appears in Open WebUI, and set `NECO_MODEL` to that exact visible ID. The Neco daemon needs no backend-specific code.

## Experimental system vitals

The host samples uptime, load, RAM, CPU temperature when available, and AMD GPU stats when Linux exposes them. The result is written to `.runtime/system-vitals.json` and mounted **read-only** into Open WebUI.

The Neco filter only injects that snapshot when the chat is actually about temperature, load, memory, uptime, hardware, or system health. Missing sensors stay missing.

```text
host Linux -> .runtime/system-vitals.json -> read-only container mount -> filter -> Neco context
```

No privileged container. No shell execution from chat. No host-control API. She can feel the fever; she cannot turn the thermostat.

## Maintenance hatch

```bash
./scripts/doctor.sh
./scripts/test-neco.sh
./scripts/start-neco.sh
systemctl --user stop echo-local-ai-v2-neco.service
sudo docker compose ps
```

`doctor.sh` validates the model through Open WebUI, so it works whether the backend is Ollama or something else.

## Development

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r neco/requirements.txt -r neco/requirements-dev.txt
ruff check neco tests scripts/setup-persona.py scripts/doctor.py
pytest -q
```

CI runs lint/tests on Python 3.10 and 3.14. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Deliberately not a framework

This is not a multi-agent system, cloud assistant, autonomous desktop operator, or production platform. It is one local character, one browser Den, one resident process, and a small amount of read-only awareness.

**Serious engineering, playful presentation.** The toaster remains under investigation.

## Credits

Built on **Open WebUI v0.11.4**, with VT323 typography, supplied Neco/cat images, and **tearreflection — upgrades**.

Original project code is MIT-licensed. Upstream software, fonts, images, and music have separate rights: [third-party notices](THIRD_PARTY_NOTICES.md) · [Open WebUI license](OPENWEBUI_LICENSE.txt).
