from __future__ import annotations

import random
import signal
import threading
from datetime import datetime

from .chat import IdleChat
from .client import NecoAPIError, OpenWebUIClient
from .config import Settings
from .generation import ThoughtGenerator, pick_tier
from .reactive import reactive_line
from .system_vitals import write_snapshot


class NecoRuntime:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.stop_event = threading.Event()
        self.client = OpenWebUIClient(settings)
        self.chat = IdleChat(settings, self.client)
        self.generator = ThoughtGenerator(settings, self.client)

    def install_signal_handlers(self) -> None:
        def stop(_signum: int, _frame: object) -> None:
            self.stop_event.set()
            self.client.cancel_active()

        signal.signal(signal.SIGTERM, stop)
        signal.signal(signal.SIGINT, stop)

    def start_vitals(self) -> threading.Thread:
        def worker() -> None:
            last_error: str | None = None
            while not self.stop_event.is_set():
                try:
                    write_snapshot()
                    last_error = None
                except Exception as exc:
                    message = f"{type(exc).__name__}: {exc}"
                    if message != last_error:
                        print(f"[vitals] snapshot unavailable: {message}", flush=True)
                        last_error = message
                self.stop_event.wait(self.settings.vitals_interval)

        thread = threading.Thread(target=worker, name="neco-vitals", daemon=True)
        thread.start()
        return thread

    def post_idle_thought(self, chat_id: str) -> str:
        reactive = reactive_line(self.settings.state_file, self.settings.owner_name)
        if reactive:
            self.chat.append(chat_id, reactive)
            print(f"[{datetime.now()}] Neco (reactive): {reactive}", flush=True)
            return reactive

        tier = pick_tier()
        if tier == "fragment":
            content = self.generator.fragment()
            self.chat.append(chat_id, content)
            print(f"[{datetime.now()}] Neco (fragment): {content}", flush=True)
            return content

        message_id, context = self.chat.reserve_assistant_message(chat_id)
        content = self.generator.generate(
            chat_id,
            message_id,
            context,
            tier,
            stop_event=self.stop_event,
        )
        if self.stop_event.is_set():
            raise InterruptedError("stopping")
        if not content:
            raise NecoAPIError("Generation finished without text. Check the model/backend stream format.")
        self.chat.save_generated(chat_id, message_id, content)
        self.chat.reload(chat_id, message_id)
        print(f"[{datetime.now()}] Neco ({tier}): {content[:120]}", flush=True)
        return content

    def run(self, *, test_mode: bool = False) -> int:
        self.install_signal_handlers()
        self.start_vitals()
        try:
            chat_id = self.chat.find_or_create()
            print(
                f"Neco idle chat ready: {self.settings.chat_title!r} in {self.settings.base_url} "
                f"(model={self.settings.model}, stream={self.settings.stream})",
                flush=True,
            )

            while not self.stop_event.is_set():
                try:
                    self.post_idle_thought(chat_id)
                except InterruptedError:
                    break
                except NecoAPIError as exc:
                    print(f"[neco] {exc}", flush=True)
                    if test_mode:
                        return 2
                    self.stop_event.wait(self.settings.error_interval)
                    continue
                except Exception as exc:
                    print(f"[neco] unexpected {type(exc).__name__}: {exc}", flush=True)
                    if test_mode:
                        return 3
                    self.stop_event.wait(self.settings.error_interval)
                    continue

                if test_mode:
                    return 0
                delay = random.uniform(self.settings.min_interval, self.settings.max_interval)
                print(f"[neco] idle for {delay / 60:.1f} minutes", flush=True)
                self.stop_event.wait(delay)
            return 0
        finally:
            self.stop_event.set()
            self.client.close()
