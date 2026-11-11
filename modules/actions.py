# -*- coding: utf-8 -*-
"""
Actions that the self can perform when ordered by the main bot.
Add more actions here as needed.
"""
from __future__ import annotations

import logging
from typing import Any, Dict

from telethon import TelegramClient
from telethon.tl.functions.account import UpdateProfileRequest, UpdateStatusRequest
from telethon.tl.functions.photos import DeletePhotosRequest, UploadProfilePhotoRequest
from telethon.tl.types import InputPhoto

logger = logging.getLogger("onyx.actions")


class ActionExecutor:
    def __init__(self, client: TelegramClient):
        self.client = client

    async def ping(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        me = await self.client.get_me()
        return {
            "status": "alive",
            "user_id": me.id,
            "username": me.username,
            "first_name": me.first_name,
        }

    async def get_me(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        me = await self.client.get_me()
        return {
            "id": me.id,
            "first_name": me.first_name,
            "last_name": me.last_name,
            "username": me.username,
            "phone": me.phone,
            "bot": me.bot,
        }

    async def update_profile(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        first_name = payload.get("first_name")
        last_name = payload.get("last_name")
        about = payload.get("about")

        kwargs = {}
        if first_name is not None:
            kwargs["first_name"] = first_name
        if last_name is not None:
            kwargs["last_name"] = last_name
        if about is not None:
            kwargs["about"] = about

        if not kwargs:
            return {"updated": False, "reason": "nothing to update"}

        await self.client(UpdateProfileRequest(**kwargs))
        return {"updated": True, "fields": list(kwargs.keys())}

    async def set_online(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        offline = bool(payload.get("offline", False))
        await self.client(UpdateStatusRequest(offline=offline))
        return {"offline": offline}

    async def send_message(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        chat_id = payload.get("chat_id")
        text = payload.get("text")
        if chat_id is None or text is None:
            raise ValueError("chat_id and text are required")

        msg = await self.client.send_message(chat_id, text)
        return {"message_id": msg.id, "chat_id": chat_id}

    async def join_chat(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        link = payload.get("link") or payload.get("username")
        if not link:
            raise ValueError("link or username required")
        entity = await self.client.get_entity(link)
        # Telethon join is usually automatic via get_entity for public, 
        # for invite links use ImportChatInviteRequest (can be added later)
        return {"joined": True, "id": getattr(entity, "id", None)}

    def build_handlers(self) -> Dict[str, Any]:
        """Return mapping action_name → coroutine"""
        return {
            "ping": self.ping,
            "get_me": self.get_me,
            "update_profile": self.update_profile,
            "set_online": self.set_online,
            "send_message": self.send_message,
            "join_chat": self.join_chat,
        }