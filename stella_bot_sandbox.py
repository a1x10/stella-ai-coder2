#!/usr/bin/env python3
"""Stella Bot Sandbox

Local Telegram/WhatsApp-style messenger emulator for testing bot logic without
real API tokens, webhooks, phones, or external messenger accounts.

Supported modes:
- Scripted scenario runner from JSON/YAML-like JSON files.
- Concurrent synthetic dialogs for load/state-machine testing.
- HTTP webhook mode compatible with many bot backends.
- In-process handler mode for Python functions/classes during unit tests.

The sandbox never sends real messages to Telegram/WhatsApp. It only simulates
updates and records bot replies locally.
"""

from __future__ import annotations

import argparse
import asyncio
import dataclasses
import datetime as dt
import importlib
import json
import random
import string
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any, Awaitable, Callable

try:
    from flask import Flask, jsonify, request
except Exception:  # pragma: no cover - optional dependency for HTTP UI/API mode
    Flask = None  # type: ignore
    request = None  # type: ignore
    jsonify = None  # type: ignore


@dataclasses.dataclass
class SandboxMessage:
    platform: str
    chat_id: str
    user_id: str
    text: str
    message_id: int
    timestamp: str = dataclasses.field(default_factory=lambda: dt.datetime.now(dt.timezone.utc).isoformat())
    username: str = "sandbox_user"
    metadata: dict[str, Any] = dataclasses.field(default_factory=dict)

    def as_telegram_update(self) -> dict[str, Any]:
        return {
            "update_id": self.message_id,
            "message": {
                "message_id": self.message_id,
                "date": int(time.time()),
                "chat": {"id": self.chat_id, "type": "private", "username": self.username},
                "from": {"id": self.user_id, "is_bot": False, "username": self.username},
                "text": self.text,
            },
        }

    def as_whatsapp_update(self) -> dict[str, Any]:
        return {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "sandbox-entry",
                    "changes": [
                        {
                            "field": "messages",
                            "value": {
                                "messaging_product": "whatsapp",
                                "metadata": {"display_phone_number": "+10000000000", "phone_number_id": "sandbox"},
                                "contacts": [{"profile": {"name": self.username}, "wa_id": self.user_id}],
                                "messages": [
                                    {
                                        "from": self.user_id,
                                        "id": f"wamid.{self.message_id}",
                                        "timestamp": str(int(time.time())),
                                        "type": "text",
                                        "text": {"body": self.text},
                                    }
                                ],
                            },
                        }
                    ],
                }
            ],
        }

    def to_update(self) -> dict[str, Any]:
        if self.platform.lower() in {"telegram", "tg"}:
            return self.as_telegram_update()
        if self.platform.lower() in {"whatsapp", "wa"}:
            return self.as_whatsapp_update()
        return dataclasses.asdict(self)


@dataclasses.dataclass
class SandboxReply:
    chat_id: str
    text: str
    platform: str = "telegram"
    timestamp: str = dataclasses.field(default_factory=lambda: dt.datetime.now(dt.timezone.utc).isoformat())
    metadata: dict[str, Any] = dataclasses.field(default_factory=dict)


class BotSandbox:
    """Deterministic local bot tester with concurrency and transcript logging."""

    def __init__(self, platform: str = "telegram", transcript_path: str | Path = ".stella/bot_sandbox_transcript.jsonl") -> None:
        self.platform = platform
        self.transcript_path = Path(transcript_path)
        self.transcript_path.parent.mkdir(parents=True, exist_ok=True)
        self.replies: list[SandboxReply] = []
        self.errors: list[str] = []
        self._message_counter = 0

    def _next_id(self) -> int:
        self._message_counter += 1
        return self._message_counter

    def log(self, event: str, payload: dict[str, Any]) -> None:
        record = {"time": dt.datetime.now(dt.timezone.utc).isoformat(), "event": event, "payload": payload}
        with self.transcript_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    def make_message(self, chat_id: str, text: str, user_id: str | None = None, username: str | None = None) -> SandboxMessage:
        user_id = user_id or chat_id
        username = username or f"user_{chat_id}"
        return SandboxMessage(platform=self.platform, chat_id=str(chat_id), user_id=str(user_id), text=text, message_id=self._next_id(), username=username)

    def capture_reply(self, chat_id: str, text: str, platform: str | None = None, **metadata: Any) -> SandboxReply:
        reply = SandboxReply(chat_id=str(chat_id), text=str(text), platform=platform or self.platform, metadata=metadata)
        self.replies.append(reply)
        self.log("bot_reply", dataclasses.asdict(reply))
        return reply

    async def dispatch_to_handler(self, handler: Callable[..., Any], message: SandboxMessage) -> Any:
        self.log("incoming_message", dataclasses.asdict(message))
        update = message.to_update()
        api = SandboxBotAPI(self, message.chat_id)
        result = handler(update, api)
        if asyncio.iscoroutine(result) or isinstance(result, Awaitable):
            result = await result
        if isinstance(result, str):
            self.capture_reply(message.chat_id, result)
        elif isinstance(result, dict) and result.get("text"):
            self.capture_reply(str(result.get("chat_id", message.chat_id)), str(result["text"]), metadata={"raw": result})
        return result

    async def dispatch_to_webhook(self, webhook_url: str, message: SandboxMessage, timeout: int = 20) -> dict[str, Any]:
        self.log("incoming_message", dataclasses.asdict(message))
        payload = json.dumps(message.to_update()).encode("utf-8")
        req = urllib.request.Request(webhook_url, data=payload, headers={"Content-Type": "application/json", "X-Stella-Bot-Sandbox": "1"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                body = response.read().decode("utf-8", errors="replace")
                result = {"status": response.status, "body": body[:10000]}
        except urllib.error.HTTPError as exc:
            result = {"status": exc.code, "body": exc.read().decode("utf-8", errors="replace")[:10000], "error": str(exc)}
            self.errors.append(str(result))
        except Exception as exc:
            result = {"status": 0, "body": "", "error": str(exc)}
            self.errors.append(str(result))
        self.log("webhook_result", result)
        return result

    async def run_script(self, scenario: dict[str, Any], handler: Callable[..., Any] | None = None, webhook_url: str | None = None) -> dict[str, Any]:
        dialogs = scenario.get("dialogs") or scenario.get("messages") or []
        if not isinstance(dialogs, list):
            raise ValueError("scenario.dialogs/messages must be a list")
        for item in dialogs:
            if isinstance(item, str):
                item = {"chat_id": "1", "text": item}
            msg = self.make_message(chat_id=str(item.get("chat_id", "1")), text=str(item.get("text", "")), user_id=str(item.get("user_id") or item.get("chat_id", "1")), username=str(item.get("username") or "sandbox_user"))
            if handler:
                await self.dispatch_to_handler(handler, msg)
            elif webhook_url:
                await self.dispatch_to_webhook(webhook_url, msg)
            else:
                self.log("dry_run", msg.to_update())
            delay = float(item.get("delay", scenario.get("delay", 0)))
            if delay > 0:
                await asyncio.sleep(delay)
        return self.summary()

    async def run_load_test(self, handler: Callable[..., Any] | None = None, webhook_url: str | None = None, users: int = 100, messages_per_user: int = 5, concurrency: int = 25) -> dict[str, Any]:
        sem = asyncio.Semaphore(max(1, concurrency))
        phrases = ["/start", "help", "status", "order " + random_token(6), "cancel", "menu", "thanks"]

        async def user_flow(user_index: int) -> None:
            async with sem:
                chat_id = str(100000 + user_index)
                for _ in range(messages_per_user):
                    text = random.choice(phrases)
                    msg = self.make_message(chat_id=chat_id, user_id=chat_id, username=f"load_user_{user_index}", text=text)
                    if handler:
                        await self.dispatch_to_handler(handler, msg)
                    elif webhook_url:
                        await self.dispatch_to_webhook(webhook_url, msg)
                    else:
                        self.log("dry_run", msg.to_update())

        await asyncio.gather(*(user_flow(i) for i in range(users)))
        return self.summary()

    def summary(self) -> dict[str, Any]:
        return {
            "platform": self.platform,
            "messages": self._message_counter,
            "replies": len(self.replies),
            "errors": self.errors[-20:],
            "transcript": str(self.transcript_path),
        }


class SandboxBotAPI:
    """Tiny fake bot API passed to in-process handlers."""

    def __init__(self, sandbox: BotSandbox, default_chat_id: str) -> None:
        self.sandbox = sandbox
        self.default_chat_id = default_chat_id

    def send_message(self, chat_id: str | int | None = None, text: str = "", **kwargs: Any) -> SandboxReply:
        return self.sandbox.capture_reply(str(chat_id or self.default_chat_id), text, metadata=kwargs)

    async def answer(self, text: str, chat_id: str | int | None = None, **kwargs: Any) -> SandboxReply:
        return self.send_message(chat_id=chat_id, text=text, **kwargs)


def random_token(length: int = 8) -> str:
    return "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(length))


def load_handler(spec: str) -> Callable[..., Any]:
    """Load `module:function` handler for in-process testing."""
    if ":" not in spec:
        raise ValueError("Handler must be in module:function format")
    module_name, func_name = spec.split(":", 1)
    module = importlib.import_module(module_name)
    handler = getattr(module, func_name)
    if not callable(handler):
        raise TypeError(f"{spec} is not callable")
    return handler


def create_http_app(sandbox: BotSandbox):
    if Flask is None:
        raise RuntimeError("Flask is not installed. Install flask or use script/load modes.")
    app = Flask(__name__)

    @app.get("/health")
    def health():
        return jsonify({"ok": True, "summary": sandbox.summary()})

    @app.post("/send")
    def send():
        data = request.get_json(force=True, silent=True) or {}
        reply = sandbox.capture_reply(str(data.get("chat_id", "1")), str(data.get("text", "")), metadata={"source": "http_api"})
        return jsonify(dataclasses.asdict(reply))

    @app.post("/simulate")
    def simulate():
        data = request.get_json(force=True, silent=True) or {}
        msg = sandbox.make_message(chat_id=str(data.get("chat_id", "1")), user_id=str(data.get("user_id") or data.get("chat_id", "1")), text=str(data.get("text", "")))
        sandbox.log("incoming_message", dataclasses.asdict(msg))
        return jsonify(msg.to_update())

    @app.get("/summary")
    def summary():
        return jsonify(sandbox.summary())

    return app


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stella Bot Sandbox — local Telegram/WhatsApp emulator")
    parser.add_argument("--platform", choices=["telegram", "whatsapp"], default="telegram")
    parser.add_argument("--scenario", help="Path to JSON scenario file")
    parser.add_argument("--handler", help="Python handler in module:function format")
    parser.add_argument("--webhook", help="Webhook URL to POST simulated updates to")
    parser.add_argument("--load", action="store_true", help="Run concurrent synthetic load test")
    parser.add_argument("--users", type=int, default=100)
    parser.add_argument("--messages-per-user", type=int, default=5)
    parser.add_argument("--concurrency", type=int, default=25)
    parser.add_argument("--serve", action="store_true", help="Start local HTTP control API")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--transcript", default=".stella/bot_sandbox_transcript.jsonl")
    return parser.parse_args(argv)


async def async_main(args: argparse.Namespace) -> int:
    sandbox = BotSandbox(platform=args.platform, transcript_path=args.transcript)
    handler = load_handler(args.handler) if args.handler else None
    if args.scenario:
        scenario = json.loads(Path(args.scenario).read_text(encoding="utf-8"))
        print(json.dumps(await sandbox.run_script(scenario, handler=handler, webhook_url=args.webhook), ensure_ascii=False, indent=2))
    if args.load:
        print(json.dumps(await sandbox.run_load_test(handler=handler, webhook_url=args.webhook, users=args.users, messages_per_user=args.messages_per_user, concurrency=args.concurrency), ensure_ascii=False, indent=2))
    if not args.scenario and not args.load and not args.serve:
        demo = {"dialogs": [{"chat_id": "1", "text": "/start"}, {"chat_id": "1", "text": "help"}, {"chat_id": "2", "text": "status"}]}
        print(json.dumps(await sandbox.run_script(demo, handler=handler, webhook_url=args.webhook), ensure_ascii=False, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    if args.serve:
        sandbox = BotSandbox(platform=args.platform, transcript_path=args.transcript)
        app = create_http_app(sandbox)
        app.run(host=args.host, port=args.port, debug=False)
        return 0
    return asyncio.run(async_main(args))


if __name__ == "__main__":
    raise SystemExit(main())
