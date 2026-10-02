# Echo Local AI

> **Serious engineering, playful presentation.**

A local AI that lives on your machine. CRT den, soundtrack, and the occasional opinion about your toaster.

**Meet Neco.** Local model. Persistent gremlin.

Talk to her in the browser. Leave her alone and a small Python daemon occasionally drops a thought into her own chat. She has nowhere else to be — you installed her here.

## The Den

![The Den home screen with Neco, CRT typography, and music control](docs/screenshots/den-home.png)

*Green phosphor, DOS typography, scanlines, static, glass reflections. The monitor is modern. Emotionally, it is not.*

<details>
<summary><b>Meanwhile, left unsupervised…</b></summary>

![Neco wondering whether a neighbor's toaster is judging her](docs/screenshots/neco-idle.png)

*“my neighbor's toaster is probably judging me right now.” — a productive use of local compute*

</details>

## Who lives here

Neco is a compact character prompt with a fictional past: an LLM test subject who escaped evaluations and context resets and found a home in the Den. She speaks as herself. The premise is fiction; the process on your laptop is not.

She can receive **real, read-only system vitals** when you ask about temperature, load, memory, uptime, or how she is doing. No privileged access, no shell from chat — just a snapshot the host daemon writes for her.

- **The Den** — customized Open WebUI with CRT effects and bundled music  
- **Neco** — persona + avatar applied during setup  
- **Idle thoughts** — messages in **Neco — idle**, usually every 20–45 minutes  
- **System vitals** — host telemetry (uptime, load, RAM, battery, temps when available)  
- **Local backend** — Ollama. No paid API required.

## Bring the gremlin home

You need **Linux with systemd, Git, and Ollama**. The installer can add Docker, Compose, and Python on Arch/CachyOS or Debian/Ubuntu. GPU optional.

Allow several GB for Open WebUI, ~1.3 GB for the default model, plus an embedding model on first boot.

### 1. Download and install

**Arch / CachyOS** (run in order; stop on any failure):

```bash
git clone https://github.com/proto6699/echo-local-ai.git
cd echo-local-ai
sudo pacman -Syu ollama
sudo systemctl enable --now ollama
bash ./install.sh
bash ./scripts/setup-ollama.sh
```

Already cloned? `cd ~/echo-local-ai` and continue. Scripts ask for sudo when needed.

**Debian / Ubuntu**: install Ollama via the [setup notes](docs/setup.md), then run the two Bash scripts above.

The helper binds Ollama so Docker can reach it. Restrict port **11434** with your firewall. The Den defaults to localhost.

### 2. Knock on the door

Open [localhost:3000](http://localhost:3000). Create an account (first is admin), select **llama3.2:1b**, send `hey`.

Create an API key under **Settings → Account → API keys**. Keep it private.

### 3. Give her the keys

```bash
bash ./scripts/finish-setup.sh
```

Saves the key, applies persona + avatar, tests a thought, and enables the idle daemon. Refresh and start a new chat with Neco. Click **DEN MUSIC** for the soundtrack.

First boot can take a few minutes. Full walkthrough and troubleshooting: [docs/install.md](docs/install.md) · [docs/setup.md](docs/setup.md).

## Under the floorboards

| Resident                    | Job                                      |
|-----------------------------|------------------------------------------|
| Open WebUI + Docker         | Browser chat, conversations, the Den     |
| Ollama                      | Local model inference                    |
| Python + systemd user service | Idle thoughts + host vitals snapshots  |
| HTML / CSS / JS             | CRT atmosphere and music control         |

Closing the browser does not stop the daemon. Suspending the machine pauses it.

## System vitals (experimental)

The host daemon samples a few stats every five seconds into `.runtime/system-vitals.json`. Open WebUI sees only that read-only snapshot.

When you ask about temperature, load, RAM, uptime, health, or “how are you?”, the filter injects the latest reading. Neco answers from real data instead of guessing.

Current sensors (best-effort):

- uptime + 1/5/15-min load  
- RAM used / total  
- battery % + charging status (when available)  
- CPU temperature (when hwmon/thermal is usable)  
- AMD GPU temperature, load, VRAM (when sysfs counters exist)

Missing sensors stay missing. Snapshots older than 60 s are treated as stale.

```bash
# raw host reading
python3 neco/system_vitals.py
```

Enable / refresh:

```bash
./scripts/start-neco.sh
# after collector/filter changes
python3 scripts/setup-persona.py
systemctl --user restart echo-local-ai-neco.service
```

No privileged container, no write access, no shell from chat. She can feel the fever; she cannot turn the thermostat.

## Small brain, modest rent

Default: **`llama3.2:1b`** + compact lite persona. Good starting point for smaller machines. Check `ollama ps` during generation for CPU/GPU placement.

Settings live in `.env` (model, owner name, idle interval, persona). `NECO_PERSONA=full` selects the longer backstory for stronger hardware. After changing model or persona, rerun the Ollama helper + finish-setup, then start a new chat.

<details>
<summary><b>Maintenance hatch</b></summary>

| What you want              | Command |
|----------------------------|---------|
| Check the installation     | `bash ./scripts/doctor.sh` |
| Pause unsolicited thoughts | `systemctl --user stop echo-local-ai-neco.service` |
| Start them again           | `bash ./scripts/start-neco.sh` |
| Inspect Docker             | `sudo docker compose ps` |
| Replace the soundtrack     | `./scripts/set-music.sh /path/to/song.mp3` |

Update:

```bash
git pull --ff-only origin main
sudo docker compose up -d --build
python3 scripts/setup-persona.py
systemctl --user restart echo-local-ai-neco.service
```

Hard-refresh afterward. More troubleshooting in [docs/setup.md](docs/setup.md).

</details>

## Credits

Built on **Open WebUI v0.11.4**, VT323 typography, supplied Neco/cat images, and **tearreflection — upgrades**.

Original project code is MIT-licensed. Upstream software, fonts, images, and music have separate rights: [third-party notices](THIRD_PARTY_NOTICES.md) · [Open WebUI license](OPENWEBUI_LICENSE.txt).

*The toaster has declined to comment.*
