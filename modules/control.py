# -*- coding: utf-8 -*-
"""
Control protocol – how the main bot talks to this self instance.

Supported channels:
1. Telegram private messages from CONTROL_USER_IDS
2. HTTP POST /command  (header: X-Account-Token)
"""
from __future__ import annotations

import json
import logging
from typing import Any, Callable, Awaitable, Dict, Optional

from aiohttp import web

logger = logging.getLogger("onyx.control")

# Type for command handlers
CommandHandler = Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]


class ControlServer:
    """Small HTTP server so the main bot can send commands."""

    def __init__(self, account_token: str, port: int = 8080):
        self.account_token = account_token
        self.port = port
        self.app = web.Application()
        self.app.router.add_get("/", self._health)
        self.app.router.add_get("/health", self._health)
        self.app.router.add_post("/command", self._command)
        self._handlers: Dict[str, CommandHandler] = {}
        self._runner: Optional[web.AppRunner] = None

    def register(self, action: str, handler: CommandHandler) -> None:
        self._handlers[action] = handler

    async def _health(self, request: web.Request) -> web.Response:
        return web.json_response({"status": "ok", "service": "onyx-self-runner"})

    async def _command(self, request: web.Request) -> web.Response:
        token = request.headers.get("X-Account-Token", "")
        if not token or token != self.account_token:
            return web.json_response({"ok": False, "error": "unauthorized"}, status=401)

        try:
            body = await request.json()
        except Exception:
            return web.json_response({"ok": False, "error": "invalid json"}, status=400)

        action = body.get("action")
        if not action or action not in self._handlers:
            return web.json_response(
                {"ok": False, "error": f"unknown action: {action}"}, status=400
            )

        try:
            result = await self._handlers[action](body)
            return web.json_response({"ok": True, "result": result})
        except Exception as e:
            logger.exception("Command %s failed", action)
            return web.json_response({"ok": False, "error": str(e)}, status=500)

    async def start(self) -> None:
        self._runner = web.AppRunner(self.app)
        await self._runner.setup()
        site = web.TCPSite(self._runner, "0.0.0.0", self.port)
        await site.start()
        logger.info("Control HTTP server listening on port %s", self.port)

    async def stop(self) -> None:
        if self._runner:
            await self._runner.cleanup()


async def handle_telegram_control(
    event,
    control_user_ids: set[int],
    account_token: str,
    handlers: Dict[str, CommandHandler],
) -> bool:
    """
    Process a private message that may be a control command from the main bot.
    Returns True if the message was a control command (so normal handlers can skip it).
    """
    if not event.is_private:
        return False
    sender = event.sender_id
    if control_user_ids and sender not in control_user_ids:
        return False

    text = (event.raw_text or "").strip()
    if not text.startswith("!onyx "):
        return False

    # Format: !onyx <token> <json_payload>
    parts = text.split(" ", 2)
    if len(parts) < 3:
        await event.reply("❌ format: !onyx <token> <json>")
        return True

    _, token, payload_raw = parts
    if token != account_token:
        await event.reply("❌ invalid token")
        return True

    try:
        payload = json.loads(payload_raw)
    except json.JSONDecodeError:
        await event.reply("❌ invalid json")
        return True

    action = payload.get("action")
    if not action or action not in handlers:
        await event.reply(f"❌ unknown action: {action}")
        return True

    try:
        result = await handlers[action](payload)
        await event.reply(f"✅ {json.dumps(result, ensure_ascii=False)[:500]}")
    except Exception as e:
        logger.exception("Telegram control command failed")
        await event.reply(f"❌ {e}")

    return True