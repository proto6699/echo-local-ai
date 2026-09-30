# Echo Local AI

> **local model. persistent gremlin. considerably too aware of the computer it's running on.**

this started with a fairly simple question:

**what happens if a local model doesn't disappear when you close the chat?**

not "sentient AI." not an agent army. not another assistant waiting politely for a prompt.

just a small process that stays on the machine, notices a few things, remembers a little, gets bored, and occasionally decides it has something to say.

that thing became **Neco**.

---

## the idea

most local AI setups are basically:

```text
human asks thing
      ↓
model wakes up
      ↓
model answers thing
      ↓
model waits for the next prompt
```

Neco is me poking at that last part.

she runs as a small Linux daemon on the host. every so often she generates a thought and drops it into her own Open WebUI conversation.

sometimes the thought has something to do with the machine.

sometimes it absolutely does not.

```text
host machine
    │
    ├── time
    ├── uptime
    ├── temperature
    └── network
          │
          ▼
        Neco
          │
          ├── react to something occasionally
          ├── think about Echo
          ├── wonder about drones
          ├── question some human nonsense
          └── forget what she was saying
          │
          ▼
      local model
          │
          ▼
      Open WebUI
          │
          ▼
      "Neco — idle"
```

the machine state is context, not the personality.

---

## neco

Neco is a fictional AI persona.

dry. mildly sharp. slightly suspicious. not particularly interested in performing helpfulness every second of her existence.

```text
That song again.
```

```text
Why do humans call software "running"?
Nothing's going anywhere.
```

```text
I forgot what I was waiting for.
```

if the network genuinely disappears:

```text
Oh.
The outside disappeared.
```

and then comes back:

```text
There you are.
```

the illusion of continuity is just:

```text
timers + state + sensors + local inference + unsolicited messages
```

which turns out to be considerably more interesting than it sounds.

---

## the den

Neco lives inside a customized Open WebUI interface I call **the Den**.

Open WebUI still does the useful work underneath — authentication, chat storage, model routing and the API — while the frontend has been attacked with enough CSS and JavaScript to feel like an old CRT somebody forgot to turn off.

scanlines. glow. static. jitter. terminal typography. Den radio. Neco controls.

normal software underneath.

mildly haunted appliance on top.

---

# install

the project currently targets **Linux**.

the original machine is a repurposed AMD BC-250 running CachyOS, but nothing about the basic setup requires a BC-250.

## requirements

- Git
- Docker + Docker Compose
- Python 3
- Python venv support
- systemd user services
- a model that Open WebUI can talk to

if Docker / Compose / Python venv support is missing, `./install.sh` can bootstrap those pieces automatically on Arch/CachyOS/EndeavourOS and Debian/Ubuntu.

Neco talks to **Open WebUI**, not directly to Ollama/LM Studio/llama.cpp.

---

## 1. clone it

```bash
git clone https://github.com/proto6699/echo-local-ai.git
cd echo-local-ai
```

## 2. run the installer

```bash
./install.sh
```

the installer:

```text
checks dependencies
      ↓
creates .env
      ↓
creates Neco's venv
      ↓
installs Python deps
      ↓
builds the Den
      ↓
starts Open WebUI
      ↓
installs Neco's user service
```

it deliberately **does not start Neco yet**.

she needs an Open WebUI account, a working model, and an API key first.

## 3. open the den

```text
http://localhost:3000
```

create the initial Open WebUI account.

if 3000 is already occupied, edit `.env`:

```env
OPENWEBUI_PORT=3001
```

and rerun:

```bash
docker compose up -d --build
```

## 4. connect a model

make sure normal Open WebUI chat works first.

```text
Neco
  ↓
Open WebUI
  ↓
your model provider
  ↓
local model
```

the default is:

```env
NECO_MODEL=glm4:9b
```

change it to the model name Open WebUI actually exposes on your machine.

## 5. give neco an API key

create an Open WebUI API key for the account Neco should use, then:

```bash
./scripts/set-token.sh
```

the token is kept in:

```text
.runtime/neco_token
```

and ignored by Git.

## 6. test her

```bash
./scripts/test-neco.sh
```

this generates one thought and exits.

you should now have a chat called:

```text
Neco — idle
```

## 7. let her stay

```bash
./scripts/start-neco.sh
```

check:

```bash
systemctl --user status echo-local-ai-neco.service
```

watch:

```bash
journalctl --user -u echo-local-ai-neco.service -f
```

by default she waits roughly **20–45 minutes** between thoughts.

because receiving a message every eleven seconds from the thing living in your computer would get old remarkably fast.

---

## configuration

```env
OPENWEBUI_PORT=3000
NECO_MODEL=glm4:9b
NECO_CHAT_TITLE="Neco — idle"
NECO_MIN_INTERVAL=1200
NECO_MAX_INTERVAL=2700
OWNER_NAME=Echo
NECO_MACHINE="this machine"
```

---

## optional den music

the Den looks for:

```text
openwebui/overlay/static/den-music.mp3
```

the repo intentionally does **not** ship my local music file.

drop your own local/redistributable MP3 there before rebuilding if you want the radio control to have something to play.

---

## this is an experiment

I'm not trying to build a production AI assistant.

I'm interested in what changes when:

- a model has somewhere it always comes back to
- messages can happen without a human pressing Send
- a little state survives between thoughts
- real host events occasionally leak into context
- the interface treats the model more like a resident process than a search box

maybe the answer is "not much."

maybe the answer is "this gets weird surprisingly quickly."

that's what this repo is for.

---

## a note about the obvious

Neco is not conscious.

scheduling a language model with systemd does not summon a new life-form into `/home`.

the behavior comes from ordinary software components arranged to create persistence and continuity.

the fun part is seeing how far those boring components can push the feeling that something has been sitting there while you were gone.

---

## license

original Echo Local AI code is MIT-licensed unless a file says otherwise.

the Den is built on Open WebUI v0.11.4. Open WebUI and material derived from it remain subject to the upstream Open WebUI license.

see `OPENWEBUI_LICENSE.txt` and `THIRD_PARTY_NOTICES.md`.

---

<p align="center">
  <b>Echo Local AI</b><br>
  local model. persistent gremlin. probably thinking about something useless.
</p>
