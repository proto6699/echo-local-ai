#!/usr/bin/env python3
import os
import sys
from pathlib import Path

import neco_monologue as neco

ROOT = Path(__file__).resolve().parent.parent

def env_int(name, default):
    value = os.getenv(name)
    return int(value) if value not in (None, "") else default

port = os.getenv("OPENWEBUI_PORT", "3000")

neco.BASE_URL = os.getenv("OPENWEBUI_URL", f"http://127.0.0.1:{port}")
neco.MODEL = os.getenv("NECO_MODEL", getattr(neco, "MODEL", "glm4:9b"))
neco.CHAT_TITLE = os.getenv("NECO_CHAT_TITLE", getattr(neco, "CHAT_TITLE", "Neco — idle"))
neco.MIN_INTERVAL = env_int("NECO_MIN_INTERVAL", getattr(neco, "MIN_INTERVAL", 1200))
neco.MAX_INTERVAL = env_int("NECO_MAX_INTERVAL", getattr(neco, "MAX_INTERVAL", 2700))

if neco.MIN_INTERVAL > neco.MAX_INTERVAL:
    raise SystemExit("NECO_MIN_INTERVAL cannot be greater than NECO_MAX_INTERVAL")

neco.TOKEN_FILE = os.getenv("NECO_TOKEN_FILE", str(ROOT / ".runtime" / "neco_token"))
neco.STATE_FILE = os.getenv("NECO_STATE_FILE", str(ROOT / ".runtime" / "neco_state.json"))

owner = os.getenv("OWNER_NAME", "Echo")
machine = os.getenv("NECO_MACHINE", "this machine")

if hasattr(neco, "BASE_PERSONA"):
    neco.BASE_PERSONA = neco.BASE_PERSONA.replace("Echo", owner)
    neco.BASE_PERSONA = neco.BASE_PERSONA.replace("BC-250", machine)

if __name__ == "__main__":
    neco.main_loop(test_mode="--test" in sys.argv)
