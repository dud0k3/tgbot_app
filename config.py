import os
import shutil
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

RAW_ENV_TEXT = (
    os.getenv(".env")
    or os.getenv("ENV")
    or os.getenv("DOTENV")
    or os.getenv("DOTENV_CONTENT")
    or ""
)

def env_value(name: str, default: str = "") -> str:
    direct = os.getenv(name)
    if direct not in (None, ""):
        return direct.strip().strip('"').strip("'")

    for line in RAW_ENV_TEXT.replace("\r", "\n").split("\n"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        if key.strip() == name:
            return value.strip().strip('"').strip("'")

    return default

BOT_TOKEN = env_value("BOT_TOKEN", "")
ADMINS = [int(x.strip()) for x in env_value("ADMINS", "").replace(";", ",").split(",") if x.strip().isdigit()]
ORDER_GROUP_ID = int(env_value("ORDER_GROUP_ID", "0") or "0")
ADMIN_USERNAMES = {
    x.strip().lower().lstrip("@")
    for x in env_value("ADMIN_USERNAMES", "dud0k3,dogaev2007").replace(";", ",").split(",")
    if x.strip()
}
_db_path_from_env = env_value("DB_PATH", "")
DB_PATH = Path(_db_path_from_env or "/data/bot.db")
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# Безопасная миграция старой локальной базы при первом переходе на /data.
# Если у хостинга уже был /app/bot.db, а /data/bot.db ещё нет — переносим базу.
try:
    _legacy_db_path = Path(__file__).resolve().parent / "bot.db"
    if not _db_path_from_env and not DB_PATH.exists() and _legacy_db_path.exists():
        shutil.copy2(_legacy_db_path, DB_PATH)
except Exception:
    pass

WEBAPP_URL = env_value("WEBAPP_URL", "")
ALLOW_USERNAME_ADMINS = env_value("ALLOW_USERNAME_ADMINS", "0").lower() in {"1", "true", "yes", "on"}

def is_admin(user_id: int) -> bool:
    return int(user_id) in ADMINS


def is_admin_identity(user_id: int, username: str | None = None) -> bool:
    if is_admin(user_id):
        return True

    # Безопаснее: username-админка отключена по умолчанию.
    # Включать только временно через ALLOW_USERNAME_ADMINS=1.
    if ALLOW_USERNAME_ADMINS and username and username.lower().lstrip("@") in ADMIN_USERNAMES:
        return True

    return False
