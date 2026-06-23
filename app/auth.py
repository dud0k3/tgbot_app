import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl
from fastapi import Header, HTTPException
from .config import get_settings


def validate_init_data(raw: str, max_age: int = 86400) -> dict:
    settings = get_settings()
    if settings.dev_mode and raw.startswith("dev:"):
        telegram_id = int(raw.split(":", 1)[1])
        return {"id": telegram_id, "first_name": "Developer", "username": "dev"}
    if not raw or not settings.bot_token:
        raise HTTPException(401, "Telegram authorization is required")
    values = dict(parse_qsl(raw, keep_blank_values=True))
    received_hash = values.pop("hash", "")
    data_check = "\n".join(f"{k}={v}" for k, v in sorted(values.items()))
    secret = hmac.new(b"WebAppData", settings.bot_token.encode(), hashlib.sha256).digest()
    expected = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(received_hash, expected):
        raise HTTPException(401, "Invalid Telegram signature")
    auth_date = int(values.get("auth_date", "0"))
    if not auth_date or time.time() - auth_date > max_age:
        raise HTTPException(401, "Telegram session expired")
    try:
        return json.loads(values["user"])
    except (KeyError, json.JSONDecodeError):
        raise HTTPException(401, "Telegram user is missing")


def telegram_user(x_telegram_init_data: str = Header(default="")) -> dict:
    return validate_init_data(x_telegram_init_data)

