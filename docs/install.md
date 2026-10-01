# full installation walkthrough — v2

[Back to the Den](../README.md) · [Troubleshooting](setup.md)

Run scripts as your normal user. They ask for `sudo` only where the host service/package manager needs it.

## 1. clone

```bash
git clone https://github.com/proto6699/echo-local-ai-v2.git
cd echo-local-ai-v2
```

## 2. install

For the bundled Ollama path:

```bash
bash ./install.sh --ollama
```

For LM Studio, llama.cpp, vLLM, or another backend you plan to connect in Open WebUI:

```bash
bash ./install.sh
```

The installer prepares `.env`, creates Neco's Python venv, starts Docker/Open WebUI, waits for `/health`, and installs the `echo-local-ai-v2-neco.service` user unit. It does **not** start Neco until an API key exists.

## 3. browser boundary

Open `http://localhost:3000` (or your configured port), create the first Open WebUI account, and verify a normal model reply.

If you used `--ollama`, the normal Open WebUI Ollama URL is:

```text
http://host.docker.internal:11434
```

Create an API key under **Settings → Account → API keys**.

## 4. finish once

```bash
bash ./scripts/finish-setup.sh
```

This saves the API key, applies Neco's persona/avatar/vitals filter, posts one test thought, enables linger, starts the daemon, and runs diagnostics.

## 5. verify

```bash
bash ./scripts/doctor.sh
journalctl --user -u echo-local-ai-v2-neco.service -n 80 --no-pager
```

A healthy Den and a valid API key do not automatically prove the configured model works; `doctor.sh` also checks that `NECO_MODEL` is visible through Open WebUI.
