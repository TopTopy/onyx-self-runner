# -*- coding: utf-8 -*-
"""
Configuration – everything comes from environment variables.
No secrets are hardcoded in this repository.
"""
import os
from typing import List, Set

def _get_int(name: str, default: int | None = None) -> int | None:
    val = os.environ.get(name)
    if val is None or val.strip() == "":
        return default
    try:
        return int(val)
    except ValueError:
        return default


def _get_list_int(name: str) -> List[int]:
    raw = os.environ.get(name, "")
    result = []
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            result.append(int(part))
    return result


# Required
API_ID: int = _get_int("API_ID") or 0
API_HASH: str = os.environ.get("API_HASH", "").strip()
SESSION_STRING: str = os.environ.get("SESSION_STRING", "").strip()
ACCOUNT_TOKEN: str = os.environ.get("ACCOUNT_TOKEN", "").strip()

# Optional
CONTROL_USER_IDS: Set[int] = set(_get_list_int("CONTROL_USER_IDS"))
MAIN_BOT_USERNAME: str = os.environ.get("MAIN_BOT_USERNAME", "").strip().lstrip("@")
PORT: int = _get_int("PORT", 8080) or 8080
LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "INFO").upper()

# Derived
IS_CONFIGURED: bool = bool(API_ID and API_HASH and SESSION_STRING and ACCOUNT_TOKEN)


def validate() -> None:
    missing = []
    if not API_ID:
        missing.append("API_ID")
    if not API_HASH:
        missing.append("API_HASH")
    if not SESSION_STRING:
        missing.append("SESSION_STRING")
    if not ACCOUNT_TOKEN:
        missing.append("ACCOUNT_TOKEN")
    if missing:
        raise RuntimeError(
            f"Missing required environment variables: {', '.join(missing)}\n"
            "See .env.example or README.md"
        )