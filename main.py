# -*- coding: utf-8 -*-
"""
ONYX Self Runner – clean public version
=======================================
No secrets inside the code. Everything comes from environment variables.
Designed to be deployed one instance per account (Railway / any host).
"""
from __future__ import annotations

import asyncio
import logging
import signal
import sys

from telethon import TelegramClient, events
from telethon.sessions import StringSession

import config
from modules.control import ControlServer, handle_telegram_control
from modules.actions import ActionExecutor

# -------------------------------------------------------------------
# Logging
# -------------------------------------------------------------------
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("onyx")

# -------------------------------------------------------------------
# Global state
# -------------------------------------------------------------------
client: TelegramClient | None = None
control_server: ControlServer | None = None
executor: ActionExecutor | None = None
_shutdown_event = asyncio.Event()


async def on_new_message(event: events.NewMessage.Event) -> None:
    """Telegram control channel."""
    if not client or not executor:
        return

    handled = await handle_telegram_control(
        event=event,
        control_user_ids=config.CONTROL_USER_IDS,
        account_token=config.ACCOUNT_TOKEN,
        handlers=executor.build_handlers(),
    )
    if handled:
        return

    # Future: normal self features (anti-delete, auto-reply, etc.) go here.
    # For now this runner focuses on being controllable by the main bot.


async def start() -> None:
    global client, control_server, executor

    config.validate()
    logger.info("Starting ONYX Self Runner...")

    client = TelegramClient(
        StringSession(config.SESSION_STRING),
        config.API_ID,
        config.API_HASH,
        connection_retries=5,
        retry_delay=2,
        auto_reconnect=True,
        device_model="ONYX-Self",
        system_version="Linux",
        app_version="1.0.0",
    )

    await client.connect()
    if not await client.is_user_authorized():
        logger.error("Session is not authorized. Check SESSION_STRING.")
        sys.exit(1)

    me = await client.get_me()
    logger.info("Logged in as %s (id=%s)", me.first_name, me.id)

    executor = ActionExecutor(client)
    handlers = executor.build_handlers()

    # HTTP control server (main bot can call it)
    control_server = ControlServer(
        account_token=config.ACCOUNT_TOKEN,
        port=config.PORT,
    )
    for action, handler in handlers.items():
        control_server.register(action, handler)
    await control_server.start()

    # Telegram control channel
    client.add_event_handler(on_new_message, events.NewMessage(incoming=True))

    logger.info("Self runner is ready. Waiting for commands from main bot.")

    # Keep running until shutdown
    await _shutdown_event.wait()


async def shutdown() -> None:
    logger.info("Shutting down...")
    _shutdown_event.set()
    if control_server:
        await control_server.stop()
    if client and client.is_connected():
        await client.disconnect()
    logger.info("Bye.")


def main() -> None:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown()))
        except NotImplementedError:
            # Windows
            pass

    try:
        loop.run_until_complete(start())
    except KeyboardInterrupt:
        loop.run_until_complete(shutdown())
    finally:
        loop.close()


if __name__ == "__main__":
    main()