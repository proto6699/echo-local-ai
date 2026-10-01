from __future__ import annotations

import time
import uuid
from typing import Any

from .client import OpenWebUIClient
from .config import Settings


class IdleChat:
    """All coupling to Open WebUI's persisted chat/history shape lives here."""

    def __init__(self, settings: Settings, client: OpenWebUIClient) -> None:
        self.settings = settings
        self.client = client

    def find_or_create(self) -> str:
        chats = self.client.json("GET", "/api/v1/chats/")
        for chat in chats:
            if chat.get("title") == self.settings.chat_title:
                return str(chat["id"])

        message_id = str(uuid.uuid4())
        message = self._message(message_id, content="", parent_id=None, done=False)
        payload = {
            "chat": {
                "title": self.settings.chat_title,
                "models": [self.settings.model],
                "messages": [message],
                "history": {"currentId": message_id, "messages": {message_id: message}},
            }
        }
        created = self.client.json("POST", "/api/v1/chats/new", payload=payload)
        return str(created["id"])

    def fetch(self, chat_id: str) -> dict[str, Any]:
        return self.client.json("GET", f"/api/v1/chats/{chat_id}")

    def context(self, chat_data: dict[str, Any]) -> list[dict[str, str]]:
        history = chat_data["chat"]["history"]
        messages = history["messages"]
        current = history.get("currentId")
        chain: list[dict[str, Any]] = []
        while current and current in messages and len(chain) < self.settings.max_context_messages:
            message = messages[current]
            chain.append(message)
            current = message.get("parentId")
        chain.reverse()
        return [
            {"role": str(message.get("role", "assistant")), "content": str(message["content"])}
            for message in chain
            if message.get("content")
        ]

    def reserve_assistant_message(self, chat_id: str) -> tuple[str, list[dict[str, str]]]:
        chat_data = self.fetch(chat_id)
        history = chat_data["chat"]["history"]
        tip_id = history["currentId"]
        tip = history["messages"].get(tip_id, {})
        context = self.context(chat_data)
        message_id = str(uuid.uuid4())
        message = self._message(message_id, content="", parent_id=tip_id, done=False)
        patch = {
            "chat": {
                "history": {
                    "currentId": message_id,
                    "messages": {
                        tip_id: {"childrenIds": list(tip.get("childrenIds", [])) + [message_id]},
                        message_id: message,
                    },
                }
            }
        }
        self.client.json("POST", f"/api/v1/chats/{chat_id}", payload=patch)
        return message_id, context

    def save_generated(self, chat_id: str, message_id: str, content: str) -> None:
        if not content:
            return
        chat_data = self.fetch(chat_id)
        saved = chat_data["chat"]["history"]["messages"].get(message_id, {})
        if saved.get("content"):
            return
        saved.update({"content": content, "done": True})
        patch = {
            "chat": {
                "history": {
                    "currentId": message_id,
                    "messages": {message_id: saved},
                }
            }
        }
        self.client.json("POST", f"/api/v1/chats/{chat_id}", payload=patch)

    def append(self, chat_id: str, content: str) -> str:
        chat_data = self.fetch(chat_id)
        history = chat_data["chat"]["history"]
        tip_id = history["currentId"]
        tip = history["messages"].get(tip_id, {})
        message_id = str(uuid.uuid4())
        message = self._message(message_id, content=content, parent_id=tip_id, done=True)
        patch = {
            "chat": {
                "history": {
                    "currentId": message_id,
                    "messages": {
                        tip_id: {"childrenIds": list(tip.get("childrenIds", [])) + [message_id]},
                        message_id: message,
                    },
                }
            }
        }
        self.client.json("POST", f"/api/v1/chats/{chat_id}", payload=patch)
        self.reload(chat_id, message_id)
        return message_id

    def reload(self, chat_id: str, message_id: str) -> None:
        self.client.json(
            "POST",
            f"/api/v1/chats/{chat_id}/messages/{message_id}/event",
            payload={"type": "chat:reload", "data": {}},
        )

    def _message(self, message_id: str, *, content: str, parent_id: str | None, done: bool) -> dict[str, Any]:
        return {
            "id": message_id,
            "role": "assistant",
            "content": content,
            "parentId": parent_id,
            "childrenIds": [],
            "model": self.settings.model,
            "modelName": self.settings.model,
            "modelIdx": 0,
            "done": done,
            "timestamp": int(time.time()),
        }
