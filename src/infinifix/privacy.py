from __future__ import annotations

import os
import re
from typing import Any

_EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_HOME_PATTERN = re.compile(r"/home/[^/\s]+")
_USERS_PATTERN = re.compile(r"/Users/[^/\s]+")
_HEX_PATTERN = re.compile(r"\b[0-9a-fA-F]{24,}\b")


def sanitize_text(value: str) -> str:
    text = value
    text = _EMAIL_PATTERN.sub("<redacted-email>", text)
    text = _HOME_PATTERN.sub("/home/<user>", text)
    text = _USERS_PATTERN.sub("/Users/<user>", text)
    text = _HEX_PATTERN.sub("<redacted-hex>", text)

    for env_name in ("USER", "USERNAME", "SUDO_USER", "LOGNAME"):
        user_value = os.getenv(env_name, "").strip()
        if user_value:
            text = text.replace(user_value, "<user>")
    return text


def sanitize_obj(obj: Any) -> Any:
    if isinstance(obj, str):
        return sanitize_text(obj)
    if isinstance(obj, list):
        return [sanitize_obj(item) for item in obj]
    if isinstance(obj, dict):
        return {str(key): sanitize_obj(value) for key, value in obj.items()}
    return obj
