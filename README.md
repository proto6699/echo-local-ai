# Echo Local AI

**local model. persistent gremlin.**

Neco lives in the Den: a CRT-styled Open WebUI with a local model, DOS typography, and a soundtrack. a small host daemon occasionally drops a thought into her own chat. serious engineering, playful presentation.

## install

Linux with systemd. bring Git and Ollama; the installer can add Docker, Compose, and Python on Arch/CachyOS or Debian/Ubuntu. [Ollama installation and troubleshooting →](docs/setup.md)

first download: several GB for Open WebUI, about **2 GB for the default model**, plus an embedding model on first boot. use a decent connection.

```bash
git clone https://github.com/proto6699/echo-local-ai.git
cd echo-local-ai
./install.sh
./scripts/setup-ollama.sh
```

open **http://localhost:3000**:

1. create your account; the first account is admin.
2. select **llama3.2:3b** and send a message to check the connection.
3. create an API key under **Settings → Account → API keys**.

then run:

```bash
./scripts/finish-setup.sh
```

paste the API key when asked. this applies Neco’s personality and avatar, generates a test thought, enables startup after logout/reboot, and runs diagnostics. an existing saved key is reused.

refresh the Den and start a new chat with **Neco** (or the existing model name). click **DEN MUSIC** for the bundled soundtrack. no manual prompt pasting, image uploads, or music copying.

first boot may take a few minutes. if models are missing or a command fails, [check setup notes](docs/setup.md). run scripts as your normal user; they ask for sudo where needed.

## the model

**`llama3.2:3b`** is the new-install default: a roughly [2 GB instruction-tuned model](https://ollama.com/library/llama3.2:3b). a practical starting point, not a guarantee of speed or character quality on every machine. the expanded persona still needs testing with it.

bigger does not mean faster. if responses crawl, run `ollama ps` while generating to see whether the model is on CPU or GPU. the old `qwen2.5:0.5b` was only a plumbing test; it failed the full persona in our direct Ollama test.

existing `.env` files are preserved. to switch an older install to the new default:

```bash
sed -i 's/^NECO_MODEL=.*/NECO_MODEL=llama3.2:3b/' .env
./scripts/setup-ollama.sh
./scripts/finish-setup.sh
```

## what stays running

Docker runs the Den. Ollama serves the model. a systemd user service runs Neco, normally posting every **20–45 minutes** in **Neco — idle**. sleep pauses her; closing the browser does not.

```bash
./scripts/doctor.sh
systemctl --user stop echo-local-ai-neco.service
./scripts/start-neco.sh
```

settings live in `.env`; the interactive personality lives in [`neco/persona.md`](neco/persona.md). the daemon has its own short idle prompt. the self-aware backstory is fiction; the resident process is real.

## update

```bash
git pull --ff-only origin main
sudo docker compose up -d --build
python3 scripts/setup-persona.py
```

hard-refresh the browser afterward. applying the persona replaces the configured model’s system prompt and avatar; other model settings are preserved.

## credits

built on **Open WebUI v0.11.4**. VT323 typography, supplied cat/Neco images, and **tearreflection — upgrades** give the Den its atmosphere.

original project code is MIT-licensed. upstream software, fonts, images, and music have separate rights; see [third-party notices](THIRD_PARTY_NOTICES.md) and [Open WebUI’s license](OPENWEBUI_LICENSE.txt).
