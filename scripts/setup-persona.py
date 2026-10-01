#!/usr/bin/env python3
"""Apply Neco's shipped persona, avatar, and vitals filter through Open WebUI."""
from __future__ import annotations

import base64
import json
from pathlib import Path
import sys
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from neco.config import Settings  # noqa: E402

VITALS_FILTER_ID = "neco_system_vitals"


class SetupError(Exception):
    """A safe, actionable setup error."""


def step(message: str) -> None:
    print("[setup] " + message, flush=True)


def main() -> None:
    step("Loading centralized config")
    settings = Settings.from_env(ROOT)
    prompt = settings.load_persona()
    if not prompt.strip():
        raise SetupError(f"{settings.persona_file.name} is empty.")

    step("Reading saved API key (contents hidden)")
    try:
        token = settings.token_file.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise SetupError("No saved API key. Run ./scripts/set-token.sh first.") from exc
    if not token:
        raise SetupError("Saved API key is empty. Run ./scripts/set-token.sh again.")

    def api(path: str, payload: dict | None = None, method: str | None = None):
        if method is None:
            method = "POST" if payload is not None else "GET"
        request = urllib.request.Request(
            settings.base_url + path,
            data=json.dumps(payload).encode() if payload is not None else None,
            headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"},
            method=method,
        )
        with urllib.request.urlopen(request, timeout=settings.api_timeout) as response:
            return json.load(response)

    step("Checking models visible to the Open WebUI account")
    models = api("/api/models")
    if settings.model not in {item.get("id") for item in models.get("data", [])}:
        raise SetupError(
            f"NECO_MODEL={settings.model!r} is not visible to this Open WebUI account. "
            "Fix the backend connection/model name and verify a normal chat first."
        )

    filter_file = ROOT / "openwebui/functions/neco_system_vitals.py"
    step("Installing experimental system-vitals filter")
    filter_payload = {
        "id": VITALS_FILTER_ID,
        "name": "Neco System Vitals",
        "content": filter_file.read_text(encoding="utf-8"),
        "meta": {"description": "Experimental read-only host telemetry context for Neco."},
    }
    try:
        existing_filter = api("/api/v1/functions/id/" + VITALS_FILTER_ID)
    except urllib.error.HTTPError as error:
        if error.code not in (401, 404):
            raise
        existing_filter = None

    if existing_filter:
        function = api("/api/v1/functions/id/" + VITALS_FILTER_ID + "/update", filter_payload)
    else:
        function = api("/api/v1/functions/create", filter_payload)
    if not function:
        raise SetupError("Open WebUI did not confirm the system-vitals filter.")

    function = api("/api/v1/functions/id/" + VITALS_FILTER_ID)
    if not function.get("is_active"):
        function = api("/api/v1/functions/id/" + VITALS_FILTER_ID + "/toggle", {}, method="POST")
    if not function or not function.get("is_active"):
        raise SetupError("The system-vitals filter could not be enabled.")

    path = "/api/v1/models/model?id=" + urllib.parse.quote(settings.model, safe="")
    step("Reading existing model configuration")
    try:
        existing = api(path)
    except urllib.error.HTTPError as error:
        if error.code != 404:
            raise
        existing = None
    if existing is not None and existing.get("write_access") is False:
        raise SetupError("This API key cannot edit the model. Use an admin key.")

    payload = {
        key: existing[key]
        for key in ("id", "base_model_id", "name", "meta", "params", "access_grants", "is_active")
        if existing and key in existing
    }
    if not existing:
        payload = dict(id=settings.model, base_model_id=None, name="Neco", meta={}, params={}, is_active=True)
    payload["params"] = dict(payload.get("params") or {}, system=prompt)

    step("Reading bundled Neco avatar")
    image = (ROOT / "openwebui/overlay/static/den-neco.png").read_bytes()
    if not image.startswith(b"\x89PNG\r\n\x1a\n"):
        raise SetupError("Bundled den-neco.png is not a valid PNG header.")
    avatar = "data:image/png;base64," + base64.b64encode(image).decode("ascii")
    payload["meta"] = dict(payload.get("meta") or {}, profile_image_url=avatar)
    payload["meta"]["capabilities"] = dict(payload["meta"].get("capabilities") or {}, builtin_tools=False)

    filter_ids = list(payload["meta"].get("filterIds") or [])
    if VITALS_FILTER_ID not in filter_ids:
        filter_ids.append(VITALS_FILTER_ID)
    payload["meta"]["filterIds"] = filter_ids

    step("Saving personality, avatar, and system-vitals filter")
    result = api("/api/v1/models/model/update" if existing else "/api/v1/models/create", payload)
    if not result:
        raise SetupError("Open WebUI did not confirm the model update.")

    step("Verifying saved configuration")
    saved = api(path)
    if not saved or saved.get("params", {}).get("system") != prompt:
        raise SetupError("Persona could not be verified after saving.")
    if saved.get("meta", {}).get("profile_image_url") != avatar:
        raise SetupError("Neco avatar could not be verified after saving.")
    if saved.get("meta", {}).get("capabilities", {}).get("builtin_tools") is not False:
        raise SetupError("Chat-only capability could not be verified after saving.")
    if VITALS_FILTER_ID not in saved.get("meta", {}).get("filterIds", []):
        raise SetupError("System-vitals filter could not be attached to Neco.")

    print(
        f"Neco {settings.persona_name} personality, avatar, and system vitals saved and verified for {settings.model}."
    )
    print("Refresh the Den and start a new chat with Neco.")


if __name__ == "__main__":
    try:
        main()
    except urllib.error.HTTPError as error:
        if error.code in (401, 403):
            message = "API key rejected. Create a fresh admin API key and run ./scripts/set-token.sh."
        else:
            message = f"Open WebUI returned HTTP {error.code}. Check its logs/API compatibility."
        print("Persona setup failed: " + message, file=sys.stderr)
        raise SystemExit(1)
    except urllib.error.URLError:
        print("Persona setup failed: cannot reach Open WebUI. Check Docker and OPENWEBUI_URL/PORT.", file=sys.stderr)
        raise SystemExit(1)
    except (SetupError, ValueError, OSError, KeyError, TypeError, json.JSONDecodeError) as error:
        print(f"Persona setup failed: {error}", file=sys.stderr)
        raise SystemExit(1)
