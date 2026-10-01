from __future__ import annotations

import os
import shlex
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_env_file(path: Path) -> None:
    """Load simple KEY=value entries without overriding an existing environment."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, value = line.partition("=")
        key = key.strip()
        if not sep or not key or key in os.environ:
            continue
        try:
            parts = shlex.split(value, comments=True)
        except ValueError as exc:
            raise ValueError(f"Invalid .env value for {key}: {exc}") from exc
        os.environ[key] = parts[0] if parts else ""


def _int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw in (None, ""):
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer, got {raw!r}") from exc


def _float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw in (None, ""):
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be a number, got {raw!r}") from exc


def _bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw in (None, ""):
        return default
    value = raw.strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be true/false, got {raw!r}")


def _path(name: str, default: Path) -> Path:
    raw = os.getenv(name)
    return Path(raw).expanduser() if raw else default


@dataclass(frozen=True, slots=True)
class Settings:
    root: Path
    base_url: str
    model: str
    chat_title: str
    min_interval: float
    max_interval: float
    error_interval: float
    max_context_messages: int
    token_file: Path
    state_file: Path
    persona_file: Path
    persona_name: str
    owner_name: str
    machine_name: str
    vitals_interval: float
    api_timeout: float
    generation_timeout: float
    retry_attempts: int
    retry_base_seconds: float
    stream: bool

    @classmethod
    def from_env(cls, root: Path = ROOT) -> Settings:
        load_env_file(root / ".env")
        port = os.getenv("OPENWEBUI_PORT", "3000")
        base_url = os.getenv("OPENWEBUI_URL", f"http://127.0.0.1:{port}").rstrip("/")
        persona_name = os.getenv("NECO_PERSONA", "lite").strip().lower()
        if persona_name not in {"lite", "full"}:
            raise ValueError("NECO_PERSONA must be 'lite' or 'full'")

        settings = cls(
            root=root,
            base_url=base_url,
            model=os.getenv("NECO_MODEL", "llama3.2:1b").strip(),
            chat_title=os.getenv("NECO_CHAT_TITLE", "Neco — idle"),
            min_interval=_float("NECO_MIN_INTERVAL", 1200),
            max_interval=_float("NECO_MAX_INTERVAL", 2700),
            error_interval=_float("NECO_ERROR_INTERVAL", 60),
            max_context_messages=_int("NECO_MAX_CONTEXT_MESSAGES", 8),
            token_file=_path("NECO_TOKEN_FILE", root / ".runtime" / "neco_token"),
            state_file=_path("NECO_STATE_FILE", root / ".runtime" / "neco_state.json"),
            persona_file=root / "neco" / ("persona-lite.md" if persona_name == "lite" else "persona.md"),
            persona_name=persona_name,
            owner_name=os.getenv("OWNER_NAME", "Echo"),
            machine_name=os.getenv("NECO_MACHINE", "this machine"),
            vitals_interval=_float("NECO_VITALS_INTERVAL", 5),
            api_timeout=_float("NECO_API_TIMEOUT", 15),
            generation_timeout=_float("NECO_GENERATION_TIMEOUT", 180),
            retry_attempts=_int("NECO_RETRY_ATTEMPTS", 4),
            retry_base_seconds=_float("NECO_RETRY_BASE_SECONDS", 2),
            stream=_bool("NECO_STREAM", True),
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        if not self.model:
            raise ValueError("NECO_MODEL cannot be empty")
        if self.min_interval < 0 or self.max_interval < 0:
            raise ValueError("Neco intervals cannot be negative")
        if self.min_interval > self.max_interval:
            raise ValueError("NECO_MIN_INTERVAL cannot be greater than NECO_MAX_INTERVAL")
        if self.error_interval < 1:
            raise ValueError("NECO_ERROR_INTERVAL must be at least 1 second")
        if self.max_context_messages < 0:
            raise ValueError("NECO_MAX_CONTEXT_MESSAGES cannot be negative")
        if self.vitals_interval < 1:
            raise ValueError("NECO_VITALS_INTERVAL must be at least 1 second")
        if self.api_timeout <= 0 or self.generation_timeout <= 0:
            raise ValueError("HTTP timeouts must be positive")
        if self.retry_attempts < 1:
            raise ValueError("NECO_RETRY_ATTEMPTS must be at least 1")
        if self.retry_base_seconds < 0:
            raise ValueError("NECO_RETRY_BASE_SECONDS cannot be negative")

    def load_persona(self) -> str:
        text = self.persona_file.read_text(encoding="utf-8")
        return text.replace("Echo", self.owner_name).replace("BC-250", self.machine_name)
