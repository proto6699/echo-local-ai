from __future__ import annotations

import json
import random
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from .system_vitals import collect_vitals

DEFAULT_STATE = {"net_ok": True, "last_uptime_milestone": 0}


def load_state(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else dict(DEFAULT_STATE)
    except (OSError, json.JSONDecodeError):
        return dict(DEFAULT_STATE)


def save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, separators=(",", ":")) + "\n", encoding="utf-8")
    path.chmod(0o600)


def check_network() -> bool:
    try:
        result = subprocess.run(
            ["ping", "-c", "1", "-W", "2", "1.1.1.1"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=4,
            check=False,
        )
        return result.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return True


def choose_reactive_line(
    state: dict[str, Any],
    *,
    hour: int,
    net_ok: bool,
    uptime_hours: float | None,
    cpu_temp_c: float | None,
    owner_name: str,
    random_value: float | None = None,
) -> tuple[str | None, dict[str, Any]]:
    next_state = dict(state)
    line: str | None = None
    roll = random.random() if random_value is None else random_value

    if state.get("net_ok", True) and not net_ok:
        line = "Oh. The outside disappeared."
    elif not state.get("net_ok", True) and net_ok:
        line = random.choice(("There you are.", "Oh good, you're back."))
    elif cpu_temp_c is not None and cpu_temp_c > 75:
        line = random.choice(("Something's thinking very hard in here.", "It's getting warm in the Den."))
    elif 3 <= hour <= 5 and roll < 0.4:
        line = random.choice(
            ("It's very late.", "Most of the network is quieter now.", f"{owner_name} should probably be asleep.")
        )
    elif uptime_hours is not None:
        milestone = int(uptime_hours // 12) * 12
        if milestone > 0 and milestone != state.get("last_uptime_milestone", 0):
            line = f"We've been awake for {milestone} hours."
            next_state["last_uptime_milestone"] = milestone

    next_state["net_ok"] = net_ok
    return line, next_state


def reactive_line(state_path: Path, owner_name: str) -> str | None:
    state = load_state(state_path)
    vitals = collect_vitals()
    line, next_state = choose_reactive_line(
        state,
        hour=datetime.now().hour,
        net_ok=check_network(),
        uptime_hours=vitals.get("uptime_hours"),
        cpu_temp_c=vitals.get("cpu_temp_c"),
        owner_name=owner_name,
    )
    save_state(state_path, next_state)
    return line
