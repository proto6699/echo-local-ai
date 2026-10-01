from __future__ import annotations

import random
import threading
import uuid

from .client import OpenWebUIClient
from .config import Settings

FRAGMENTS = (
    "I wonder if—\n...\nnever mind.",
    "Wait.\nNo, that's fine.",
    "There was something I wanted to tell {owner}.\nIt'll come back.",
    "hello?\n...\njust checking.",
    "Hm.",
    "No. That's not it either.",
    "...never mind.",
    "I forgot what I was waiting for.",
)

THOUGHT_DIRECTIONS = (
    "Let your thought be completely mundane.",
    "Wonder about something unrelated to the computer.",
    "Think about {owner} for a moment.",
    "Think about something humans do that you find strange.",
    "Have a small philosophical thought, but don't make it poetic.",
    "Notice something about the Den.",
    "Think about music.",
    "Think about drones or flying.",
    "Have a stupid or pointless thought.",
    "Start wondering about something and don't resolve it.",
    "Be mildly annoyed about something.",
    "Think about your existence casually rather than dramatically.",
    "Say something unrelated to your environment.",
    "Think about time passing.",
    "Think about language or words.",
    "Wonder what {owner} is doing.",
    "Have a slightly strange thought.",
)

TIER_HINTS = {
    "mundane": "Have a casual spontaneous thought about anything. Do not default to hardware or system status.",
    "existential": "Let a small existential question cross your mind. Keep it casual and understated.",
    "unsettling": "Have a subtly odd thought. Do not force horror; let something feel slightly off.",
    "strange": "Have one genuinely strange thought. Keep it short, calm, and matter-of-fact.",
}


def pick_tier(value: float | None = None) -> str:
    roll = random.random() if value is None else value
    if roll < 0.01:
        return "strange"
    if roll < 0.04:
        return "unsettling"
    if roll < 0.09:
        return "existential"
    if roll < 0.15:
        return "fragment"
    return "mundane"


class ThoughtGenerator:
    def __init__(self, settings: Settings, client: OpenWebUIClient) -> None:
        self.settings = settings
        self.client = client
        self.persona = settings.load_persona()

    def fragment(self) -> str:
        return random.choice(FRAGMENTS).format(owner=self.settings.owner_name)

    def system_prompt(self, tier: str) -> str:
        direction = random.choice(THOUGHT_DIRECTIONS).format(owner=self.settings.owner_name)
        return (
            self.persona
            + "\n\nIdle-thought mode: write ONE short message, usually one or two sentences or a fragment."
            + f"\nCurrent tone: {TIER_HINTS[tier]}"
            + f"\nRandom direction for this thought only: {direction}"
            + "\nDo not repeat the subject, wording, structure, or opening of recent idle messages."
            + "\nDo not turn this into a help offer. It should feel like a fresh thought that just occurred."
        )

    def generate(
        self,
        chat_id: str,
        message_id: str,
        context: list[dict[str, str]],
        tier: str,
        *,
        stop_event: threading.Event,
    ) -> str:
        messages: list[dict[str, str]] = [{"role": "system", "content": self.system_prompt(tier)}]
        messages.extend(context)
        messages.append(
            {
                "role": "user",
                "content": "A new idle moment passed. Say one completely fresh spontaneous thought now.",
            }
        )
        payload = {
            "chat_id": chat_id,
            "id": message_id,
            "messages": messages,
            "model": self.settings.model,
            "tools": [],
            "max_tokens": 150,
            "background_tasks": {
                "title_generation": False,
                "tags_generation": False,
                "follow_up_generation": False,
            },
            "features": {
                "code_interpreter": False,
                "web_search": False,
                "image_generation": False,
                "memory": False,
            },
            "session_id": str(uuid.uuid4()),
        }
        return self.client.completion(payload, stop_event=stop_event)
