from pathlib import Path

import pytest

from neco.config import Settings


def test_config_defaults(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    for key in (
        "OPENWEBUI_URL",
        "OPENWEBUI_PORT",
        "NECO_MODEL",
        "NECO_PERSONA",
        "NECO_MIN_INTERVAL",
        "NECO_MAX_INTERVAL",
        "NECO_STREAM",
    ):
        monkeypatch.delenv(key, raising=False)
    settings = Settings.from_env(tmp_path)
    assert settings.base_url == "http://127.0.0.1:3000"
    assert settings.model == "llama3.2:1b"
    assert settings.stream is True
    assert settings.persona_file == tmp_path / "neco" / "persona-lite.md"


def test_invalid_interval(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("NECO_MIN_INTERVAL", "20")
    monkeypatch.setenv("NECO_MAX_INTERVAL", "10")
    with pytest.raises(ValueError, match="MIN_INTERVAL"):
        Settings.from_env(tmp_path)


def test_invalid_bool(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("NECO_STREAM", "sometimes")
    with pytest.raises(ValueError, match="true/false"):
        Settings.from_env(tmp_path)
