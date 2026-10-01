# Echo Local AI

> **local model. persistent gremlin. considerably too aware of the computer it's running on.**

most local AI is a vending machine. you ask, it answers, it goes dark.

this started with one question: **what happens if the model doesn't disappear when you close the chat?**

the answer is **Neco**: a small daemon that lives on your machine, notices a few things, remembers a little, gets bored, and occasionally decides it has something to say. no agent army. no "sentient AI." just a resident process with opinions.

---

## how she works

```
host: time · uptime · temperature · network
                 │
                 ▼
               Neco  ──  thinks every ~20–45 min
                 │
                 ▼
            local model  (via Open WebUI)
                 │
                 ▼
        "Neco — idle"  ← a chat in the Den
```

machine state is context, not personality. the illusion of continuity is just:

```
timers + state + sensors + local inference + unsolicited messages
```

boring parts. surprisingly good trick.

## meet neco

dry. mildly sharp. slightly suspicious. not interested in performing helpfulness every second of her existence.

```
That song again.
```
```
Why do humans call software "running"?
Nothing's going anywhere.
```

if the network drops: *"Oh. The outside disappeared."*
when it comes back: *"There you are."*

she is **not conscious**. scheduling a language model with systemd does not summon a life-form into `/home`. it just feels like something's been sitting there while you were gone.

## the den

Neco lives in **the Den**: Open WebUI wearing a CRT costume. scanlines, glow, static, jitter, locally bundled VT323 pixel-terminal type, and a radio. the Neco QC widget has been removed.

Open WebUI still does the real work underneath (auth, chat storage, API). the Den is what happens when CSS gets out of hand.

---

# install

**linux only for now.** built on an AMD BC-250 running CachyOS, but nothing requires one. tested on a plain laptop too.

you need: Git, Docker + Compose, Python 3 with venv, systemd user services, and a model server. if Docker or Python bits are missing, `./install.sh` can install them on Arch/CachyOS/EndeavourOS and Debian/Ubuntu.

> **heads up on data:** the first build pulls the Open WebUI base image (several GB), and on first boot it fetches a small embedding model. if you're on a metered connection, do this on wifi.

## 1. get a model running (Ollama)

Neco talks to Open WebUI, and Open WebUI talks to your model. Ollama is the easy way to have one.

```bash
# Arch / CachyOS
sudo pacman -S ollama            # or ollama-vulkan for GPU via Vulkan

# Debian / Ubuntu
curl -fsSL https://ollama.com/install.sh | sh
```

Open WebUI runs inside Docker, so Ollama has to listen on more than localhost:

```bash
sudo mkdir -p /etc/systemd/system/ollama.service.d
printf '[Service]\nEnvironment="OLLAMA_HOST=0.0.0.0"\n' | sudo tee /etc/systemd/system/ollama.service.d/override.conf
sudo systemctl daemon-reload
sudo systemctl enable --now ollama
```

pull something small and make sure it talks:

```bash
ollama pull qwen2.5:0.5b
ollama run qwen2.5:0.5b "say hi"
```

**firewall:** if you use `ufw`, Docker can't reach Ollama until you allow it (the container just times out):

```bash
sudo ufw allow from 172.16.0.0/12 to any port 11434 proto tcp
sudo ufw reload
```

(`firewalld` users: trust Docker's subnet instead.)

LM Studio or a llama.cpp server works too. add it in Open WebUI as an OpenAI-compatible connection.

## 2. clone and install

```bash
git clone https://github.com/proto6699/echo-local-ai.git
cd echo-local-ai
./install.sh
```

it checks dependencies, creates `.env` (with a generated secret key), builds Neco's Python venv, builds and starts the Den, and installs Neco's user service. it deliberately **does not start Neco**. she needs an account, a model, and a key first.

when it finishes, the container may show `unhealthy` for a couple of minutes on first boot. that's the embedding model downloading. give it time.

## 3. open the den

go to **http://localhost:3000** and create your account. the first account becomes admin. this is the account Neco will use.

port taken? set `OPENWEBUI_PORT=3001` in `.env`, then `docker compose up -d --build`.

## 4. connect your model

in the Den: **Admin Settings → Connections → Ollama API**, turn it on, set the URL to:

```
http://host.docker.internal:11434
```

hit verify, save, then start a normal chat and confirm the model answers. **do not skip this.** if chat doesn't work, Neco won't either.

## 5. give neco a key

create an API key in **Settings → Account → API keys**, then:

```bash
./scripts/set-token.sh
```

it's stored in `.runtime/neco_token`, which Git ignores.

## 6. test her, then let her stay

```bash
./scripts/test-neco.sh      # one thought, then exits
```

a chat called **Neco — idle** should appear in the Den. if it does:

```bash
./scripts/start-neco.sh
loginctl enable-linger $USER    # keeps her alive after you log out
```

check on her:

```bash
systemctl --user status echo-local-ai-neco.service --no-pager
journalctl --user -u echo-local-ai-neco.service -f
```

by default she waits **20–45 minutes** between thoughts. a message every eleven seconds would get old fast.

---

## picking a model

set `NECO_MODEL` in `.env` to **exactly** what `ollama list` (and the Den's model dropdown) shows.

| model | size | notes |
|---|---|---|
| `qwen2.5:0.5b` | ~0.4 GB | smoke-test only. rough writing. |
| `llama3.2:3b` | ~2 GB | good small default for a laptop |
| `qwen2.5:3b` | ~2 GB | similar, follows persona well |
| `glm4:9b` | ~5 GB+ | repo default. needs real hardware |

avoid "thinking" models. their reasoning text can leak into Neco's messages.

change models any time:

```bash
nano .env
systemctl --user restart echo-local-ai-neco.service
```

## configuration

```
OPENWEBUI_PORT=3000
NECO_MODEL=glm4:9b
NECO_CHAT_TITLE="Neco — idle"
NECO_MIN_INTERVAL=1200     # seconds
NECO_MAX_INTERVAL=2700
OWNER_NAME=Echo            # what she calls you
NECO_MACHINE="this machine"
```

## when it breaks

| symptom | cause / fix |
|---|---|
| Den says **no models available**, but `ollama run` works | the container can't reach Ollama. check `OLLAMA_HOST=0.0.0.0` and the firewall rule above |
| image pull dies with `timeout awaiting response headers` | flaky connection. retry the pull until it finishes (finished layers are kept): `until sudo docker pull ghcr.io/open-webui/open-webui:v0.11.4; do sleep 5; done`, then rerun `./install.sh` |
| `pacman` 404s or "signature is invalid" | mirror out of sync. `sudo cachyos-rate-mirrors && sudo pacman -Syu` |
| `test-neco.sh` errors on the model | `NECO_MODEL` doesn't match the name in `ollama list` |
| `systemctl` output looks frozen | it's a pager. press `q`, or add `--no-pager` |
| Neco vanishes after logout or reboot | run `loginctl enable-linger $USER` and confirm the service is enabled |
| `buildx plugin not found` warning | harmless. Docker falls back to the classic builder |

laptop note: suspend pauses everything, including her timers. she's patient, not immortal.

## den music

the Den looks for `openwebui/overlay/static/den-music.mp3`. the repo doesn't ship my music file. drop in your own (redistributable) MP3 and rebuild if you want the radio to play something.

## this is an experiment

not a production assistant. i'm poking at what changes when a model has somewhere it always comes back to, messages can happen without anyone pressing Send, a little state survives between thoughts, and real host events leak into context.

maybe the answer is "not much." maybe it gets weird surprisingly quickly. that's what this repo is for.

## license

original Echo Local AI code is MIT-licensed unless a file says otherwise. the Den is built on Open WebUI v0.11.4, which remains under its upstream license. see `OPENWEBUI_LICENSE.txt` and `THIRD_PARTY_NOTICES.md`.

---

**Echo Local AI** · local model. persistent gremlin. probably thinking about something useless.

## den visuals

the DOS-style VT323 font is bundled locally at a larger reading size. the cat photo is the browser-tab icon; the supplied Neco illustration is the model/chat avatar. after updating and rebuilding an existing installation, run `python3 scripts/setup-persona.py` to apply the model avatar, then hard-refresh the browser. the account/user avatar is separate.
