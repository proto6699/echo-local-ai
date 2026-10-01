from __future__ import annotations

import json
import threading
import time
from typing import Any, Iterator

import requests

from .config import Settings


class NecoAPIError(RuntimeError):
    """Actionable Open WebUI/API failure."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class OpenWebUIClient:
    def __init__(self, settings: Settings, session: requests.Session | None = None) -> None:
        self.settings = settings
        self.session = session or requests.Session()
        self._active_lock = threading.Lock()
        self._active_response: requests.Response | None = None

    def cancel_active(self) -> None:
        """Close an in-flight streamed completion, if one exists."""
        with self._active_lock:
            response = self._active_response
        if response is not None:
            response.close()

    def close(self) -> None:
        self.cancel_active()
        self.session.close()

    def _token(self) -> str:
        try:
            token = self.settings.token_file.read_text(encoding="utf-8").strip()
        except OSError as exc:
            raise NecoAPIError(
                f"API key file is missing/unreadable: {self.settings.token_file}. "
                "Run ./scripts/set-token.sh."
            ) from exc
        if not token:
            raise NecoAPIError("API key file is empty. Run ./scripts/set-token.sh.")
        return token

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token()}",
            "Content-Type": "application/json",
        }

    def request(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        timeout: float | tuple[float, float] | None = None,
        stream: bool = False,
    ) -> requests.Response:
        url = f"{self.settings.base_url}{path}"
        timeout = timeout or self.settings.api_timeout
        last_error: Exception | None = None

        for attempt in range(1, self.settings.retry_attempts + 1):
            try:
                response = self.session.request(
                    method,
                    url,
                    headers=self._headers(),
                    json=payload,
                    timeout=timeout,
                    stream=stream,
                )
            except (requests.ConnectionError, requests.Timeout) as exc:
                last_error = exc
                if attempt == self.settings.retry_attempts:
                    break
                self._backoff(attempt)
                continue

            if response.status_code in {401, 403}:
                response.close()
                raise NecoAPIError(
                    "Open WebUI rejected the API key. Create/refresh an admin API key, "
                    "then run ./scripts/set-token.sh.",
                    status_code=response.status_code,
                )

            if response.status_code == 404:
                detail = self._detail(response)
                response.close()
                raise NecoAPIError(
                    f"Open WebUI endpoint/model was not found at {path}. {detail}".strip(),
                    status_code=404,
                )

            if response.status_code == 429 or response.status_code >= 500:
                last_error = NecoAPIError(
                    f"Open WebUI returned HTTP {response.status_code}: {self._detail(response)}",
                    status_code=response.status_code,
                )
                response.close()
                if attempt == self.settings.retry_attempts:
                    break
                self._backoff(attempt)
                continue

            try:
                response.raise_for_status()
            except requests.HTTPError as exc:
                detail = self._detail(response)
                response.close()
                raise NecoAPIError(
                    f"Open WebUI request failed with HTTP {exc.response.status_code}: {detail}",
                    status_code=exc.response.status_code,
                ) from exc
            return response

        if isinstance(last_error, NecoAPIError):
            raise last_error
        raise NecoAPIError(
            f"Cannot reach Open WebUI at {self.settings.base_url} after "
            f"{self.settings.retry_attempts} attempts. Check Docker, /health, and OPENWEBUI_URL."
        ) from last_error

    def _backoff(self, attempt: int) -> None:
        delay = min(20.0, self.settings.retry_base_seconds * (2 ** (attempt - 1)))
        if delay:
            time.sleep(delay)

    @staticmethod
    def _detail(response: requests.Response) -> str:
        try:
            data = response.json()
        except ValueError:
            return response.text[:240].strip()
        if isinstance(data, dict):
            for key in ("detail", "message", "error"):
                value = data.get(key)
                if value:
                    return str(value)[:240]
        return str(data)[:240]

    def json(self, method: str, path: str, *, payload: dict[str, Any] | None = None) -> Any:
        response = self.request(method, path, payload=payload)
        try:
            return response.json()
        except ValueError as exc:
            raise NecoAPIError(f"Open WebUI returned non-JSON data for {path}.") from exc
        finally:
            response.close()

    def completion(
        self,
        payload: dict[str, Any],
        *,
        stop_event: threading.Event,
    ) -> str:
        if not self.settings.stream:
            response = self.request(
                "POST",
                "/api/chat/completions",
                payload={**payload, "stream": False},
                timeout=(self.settings.api_timeout, self.settings.generation_timeout),
            )
            try:
                data = response.json()
                return str(data["choices"][0]["message"]["content"])
            except (ValueError, KeyError, IndexError, TypeError) as exc:
                raise NecoAPIError("Generation returned an unexpected response shape.") from exc
            finally:
                response.close()

        response = self.request(
            "POST",
            "/api/chat/completions",
            payload={**payload, "stream": True},
            timeout=(self.settings.api_timeout, self.settings.generation_timeout),
            stream=True,
        )
        chunks: list[str] = []
        with self._active_lock:
            self._active_response = response
        try:
            for data in self._sse_json(response.iter_lines(decode_unicode=True)):
                if stop_event.is_set():
                    raise InterruptedError("generation cancelled")
                choices = data.get("choices") if isinstance(data, dict) else None
                if not choices:
                    continue
                first = choices[0] or {}
                delta = first.get("delta") or {}
                text = delta.get("content")
                if text is None:
                    message = first.get("message") or {}
                    text = message.get("content")
                if text:
                    chunks.append(str(text))
        finally:
            with self._active_lock:
                if self._active_response is response:
                    self._active_response = None
            response.close()
        return "".join(chunks).strip()

    @staticmethod
    def _sse_json(lines: Iterator[str | bytes]) -> Iterator[dict[str, Any]]:
        for raw in lines:
            if not raw:
                continue
            line = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else raw
            line = line.strip()
            if line.startswith("data:"):
                line = line[5:].strip()
            if not line or line == "[DONE]":
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(data, dict):
                yield data
