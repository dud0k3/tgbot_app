import hashlib
import hmac
import json
import time
from urllib.parse import urlencode
from app.auth import validate_init_data
from app.config import get_settings


def test_telegram_init_data_signature(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "bot_token", "123456:test-token")
    user = json.dumps({"id": 42, "first_name": "Test"}, separators=(",", ":"))
    values = {"auth_date": str(int(time.time())), "query_id": "AAE", "user": user}
    check = "\n".join(f"{k}={v}" for k, v in sorted(values.items()))
    secret = hmac.new(b"WebAppData", settings.bot_token.encode(), hashlib.sha256).digest()
    values["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    assert validate_init_data(urlencode(values))["id"] == 42

