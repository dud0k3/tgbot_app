import hashlib
import hmac
import json
import logging
import os
import re
import sqlite3
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from image_storage import UPLOAD_DIR, ensure_upload_dir, local_image_exists, image_storage_status
from db import init_db

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

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
OLD_BOT_TOKEN = env_value("OLD_BOT_TOKEN", "")
ADMINS = [int(x.strip()) for x in env_value("ADMINS", "").replace(";", ",").split(",") if x.strip().isdigit()]
ADMIN_USERNAMES = {x.strip().lower().lstrip("@") for x in env_value("ADMIN_USERNAMES", "dud0k3,dogaev2007").replace(";", ",").split(",") if x.strip()}
ORDER_GROUP_ID = int(env_value("ORDER_GROUP_ID", "0") or "0")
BOT_USERNAME = env_value("BOT_USERNAME", "").lstrip("@")
MINI_APP_NAME = env_value("MINI_APP_NAME", env_value("BOT_APP_NAME", "app")).strip().strip("/")
DEBUG_TOKEN = env_value("DEBUG_TOKEN", "")
ALLOW_USERNAME_ADMINS = env_value("ALLOW_USERNAME_ADMINS", "0").lower() in {"1", "true", "yes", "on"}
DB_PATH = Path(env_value("DB_PATH", str(Path(__file__).resolve().parent.parent / "bot.db")))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
THANKS_ORDER_IMAGE = Path(__file__).resolve().parent.parent / 'frontend' / 'public' / 'thanks-order.png'
MOSCOW_TIMEZONE = ZoneInfo("Europe/Moscow")

app = FastAPI(title="SYNDICATE API")
ensure_upload_dir()
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

app.add_middleware(
    CORSMiddleware,
    # Mini App работает с того же домена. Для API не нужны cross-site credentials.
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-Telegram-Init-Data", "X-Referral-Start-Param", "X-Debug-Token"],
)

def connect():
    con = sqlite3.connect(DB_PATH, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    con.execute("PRAGMA busy_timeout=5000")
    return con

def tg_api(method: str, payload: dict | None = None):
    if not BOT_TOKEN:
        return None

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    data = None if payload is None else urllib.parse.urlencode(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST" if payload else "GET")

    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        logging.warning("Telegram API call failed: %s", e)
        return {"ok": False, "error": str(e)}

def tg_api_multipart(method: str, fields: dict, file_field: str, file_path: Path, content_type: str = "image/png"):
    if not BOT_TOKEN or not file_path.exists():
        return None

    boundary = "----SyndicateBoundary7MA4YWxkTrZu0gW"
    body = bytearray()

    for key, value in fields.items():
        if value is None:
            continue
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode("utf-8"))
        body.extend(str(value).encode("utf-8"))
        body.extend(b"\r\n")

    body.extend(f"--{boundary}\r\n".encode("utf-8"))
    body.extend(
        f'Content-Disposition: form-data; name="{file_field}"; filename="{file_path.name}"\r\n'.encode("utf-8")
    )
    body.extend(f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"))
    body.extend(file_path.read_bytes())
    body.extend(b"\r\n")
    body.extend(f"--{boundary}--\r\n".encode("utf-8"))

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    req = urllib.request.Request(
        url,
        data=bytes(body),
        method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        logging.warning("Telegram multipart API call failed: %s", e)
        return {"ok": False, "error": str(e)}


def parse_init_data(init_data: str):
    if not init_data:
        raise HTTPException(status_code=401, detail="Telegram initData is empty")

    parsed = urllib.parse.parse_qs(init_data, keep_blank_values=True)
    data = {k: v[0] for k, v in parsed.items()}

    received_hash = data.pop("hash", None)
    if not received_hash:
        raise HTTPException(status_code=401, detail="Telegram hash is missing")

    check_string = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))
    secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    calculated_hash = hmac.new(secret_key, check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(calculated_hash, received_hash):
        raise HTTPException(status_code=401, detail="Invalid Telegram initData")

    try:
        auth_date = int(data.get("auth_date", "0") or "0")
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid Telegram auth_date")

    if auth_date and time.time() - auth_date > 86400:
        raise HTTPException(status_code=401, detail="Telegram initData expired")

    if auth_date and auth_date - time.time() > 300:
        raise HTTPException(status_code=401, detail="Telegram initData date is invalid")

    user_raw = data.get("user")
    if not user_raw:
        raise HTTPException(status_code=401, detail="Telegram user is missing")

    try:
        user = json.loads(user_raw)
        if data.get("start_param"):
            user["start_param"] = data.get("start_param")
        return user
    except json.JSONDecodeError:
        raise HTTPException(status_code=401, detail="Telegram user payload is invalid")

def get_referral_start_param_from_request(request: Request) -> str | None:
    # Основной источник — подписанный Telegram initData.
    # Но на части клиентов прямой Mini App link может отдавать start_param в tgWebAppStartParam,
    # поэтому frontend дополнительно передаёт X-Referral-Start-Param.
    # Значение всё равно нормализуется и применяется только если у пользователя ещё нет referrer_id.
    value = (
        request.headers.get("X-Referral-Start-Param")
        or request.query_params.get("start_param")
        or request.query_params.get("startapp")
        or ""
    )
    return normalize_referral_code(value)


def get_user_from_request(request: Request, x_telegram_init_data: str | None = Header(default=None)):
    if not BOT_TOKEN:
        raise HTTPException(status_code=500, detail="BOT_TOKEN is empty")

    init_data = x_telegram_init_data or request.headers.get("X-Telegram-Init-Data")
    fallback_ref_code = get_referral_start_param_from_request(request)

    # Разрешаем браузерный тест без Telegram только на localhost
    host = request.headers.get("host", "")
    if not init_data and ("127.0.0.1" in host or "localhost" in host):
        user = {"id": 777001, "username": "test_user"}
        if fallback_ref_code:
            user["start_param"] = fallback_ref_code
        register_telegram_user(user)
        return user

    user = parse_init_data(init_data or "")

    if fallback_ref_code and not user.get("start_param"):
        user["start_param"] = fallback_ref_code

    register_telegram_user(user)
    return user

def file_url(file_id=None, local_path=None):
    # Сначала отдаём локальный файл /uploads/...
    # Если файла нет на диске, падаем обратно на Telegram file_id.
    if local_path and local_image_exists(local_path):
        return str(local_path)

    if not file_id:
        return None

    return f"/api/tg-file?file_id={urllib.parse.quote(str(file_id))}"

MAX_CART_QUANTITY = 99
MAX_COMMENT_LENGTH = 500
MAX_TEXT_FIELD_LENGTH = 80
PICKUP_POINTS = {"Ипподром", "Раменское", "Фабричная", "Есенинская", "Ильинская", "Кратово", "Отдых"}


def clean_text(value: str | None, limit: int = MAX_TEXT_FIELD_LENGTH) -> str:
    value = str(value or "").replace("\x00", "").strip()
    value = re.sub(r"\s+", " ", value)
    return value[:limit]


def debug_allowed(request: Request, x_telegram_init_data: str | None = None) -> bool:
    token = request.headers.get("X-Debug-Token")

    if DEBUG_TOKEN and token and hmac.compare_digest(str(token), DEBUG_TOKEN):
        return True

    try:
        user = parse_init_data(x_telegram_init_data or request.headers.get("X-Telegram-Init-Data") or "")
        return int(user.get("id", 0)) in ADMINS
    except Exception:
        return False


def file_id_is_public_image(file_id: str) -> bool:
    if not file_id:
        return False

    with connect() as con:
        row = con.execute(
            """
            SELECT 1 FROM categories WHERE image_id = ?
            UNION
            SELECT 1 FROM products WHERE photo_id = ?
            LIMIT 1
            """,
            (file_id, file_id)
        ).fetchone()

    return bool(row)


def parse_variant_stock_options(raw: str | None, fallback_stock: int = 0):
    if not raw:
        return []

    text = str(raw).strip()

    if not text:
        return []

    if text.startswith("["):
        try:
            data = json.loads(text)
            result = []
            seen = set()

            for item in data:
                if isinstance(item, dict):
                    name = str(item.get("name") or "").strip()
                    stock = int(item.get("stock") or 0)
                else:
                    name = str(item or "").strip()
                    stock = int(fallback_stock or 0)

                if not name or name == "-":
                    continue

                key = name.lower()

                if key in seen:
                    continue

                result.append({"name": name, "stock": max(stock, 0)})
                seen.add(key)

            return result
        except Exception:
            pass

    result = []
    seen = set()

    normalized = text.replace(";", "\n")
    for line in normalized.splitlines():
        for chunk in line.split(","):
            value = chunk.strip()
            if value and value != "-":
                key = value.lower()
                if key not in seen:
                    result.append({"name": value, "stock": max(int(fallback_stock or 0), 0)})
                    seen.add(key)

    return result


def variant_options_have_explicit_stock(raw: str | None):
    if not raw:
        return False

    text = str(raw).strip()

    if not text.startswith("["):
        return False

    try:
        data = json.loads(text)
        return any(isinstance(item, dict) and "stock" in item for item in data)
    except Exception:
        return False


def public_variants(raw: str | None):
    return [v["name"] for v in parse_variant_stock_options(raw) if int(v["stock"] or 0) > 0]


def variant_stock_for(raw: str | None, variant: str | None, fallback_stock: int = 0):
    variants = parse_variant_stock_options(raw, fallback_stock=fallback_stock)

    if not variants:
        return int(fallback_stock or 0)

    variant = (variant or "").strip()

    for item in variants:
        if item["name"] == variant:
            return int(item["stock"] or 0)

    return 0


def parse_variants(raw: str | None):
    return public_variants(raw)

def category_dict(row):
    d = dict(row)
    d["image_url"] = file_url(d.get("image_id"), d.get("image_path"))
    return d

def product_dict(row):
    d = dict(row)
    d["image_url"] = file_url(d.get("photo_id"), d.get("photo_path"))
    fallback_stock = int(d.get("stock") if d.get("stock") is not None else d.get("quantity") or 0)
    variant_rows = parse_variant_stock_options(d.get("variant_options"), fallback_stock=fallback_stock)
    d["variants"] = [item["name"] for item in variant_rows if int(item["stock"] or 0) > 0]
    d["variant_stock"] = {
        item["name"]: int(item["stock"] or 0)
        for item in variant_rows
    }
    return d

def cart_item_dict(row):
    d = dict(row)

    product_exists = d.get("db_product_id") is not None

    if not product_exists:
        quantity = int(d.get("quantity") or 0)
        return {
            "product_id": int(d.get("product_id") or 0),
            "variant": d.get("variant") or "",
            "quantity": quantity,
            "name": "Товар удалён",
            "price": 0,
            "image_url": None,
            "description": "",
            "stock": 0,
            "available_stock": 0,
            "stock_status": "out",
            "stock_message": "Товар больше недоступен. Удалите его из корзины.",
            "can_checkout": False,
            "variants": [],
            "variant_stock": {},
        }

    quantity = int(d.get("quantity") or 0)
    stock = int(d.get("stock") or 0)
    variant = (d.get("variant") or "").strip()
    variant_options = d.get("variant_options")
    variants = parse_variant_stock_options(variant_options, fallback_stock=stock)

    if variants:
        available_stock = variant_stock_for(variant_options, variant, fallback_stock=stock)
    else:
        available_stock = stock

    if available_stock <= 0:
        stock_status = "out"
        if variant:
            stock_message = f"Вкус «{variant}» закончился. Удалите товар из корзины."
        else:
            stock_message = "Товар закончился. Удалите его из корзины."
    elif quantity > available_stock:
        stock_status = "insufficient"
        stock_message = f"На складе осталось {available_stock} шт. Уменьшите количество или удалите товар."
    else:
        stock_status = "ok"
        stock_message = ""

    item = product_dict(row)
    item["available_stock"] = int(available_stock)
    item["stock_status"] = stock_status
    item["stock_message"] = stock_message
    item["can_checkout"] = stock_status == "ok"
    return item

def ensure_image_storage_columns():
    with connect() as con:
        category_cols = [r["name"] for r in con.execute("PRAGMA table_info(categories)").fetchall()]
        product_cols = [r["name"] for r in con.execute("PRAGMA table_info(products)").fetchall()]

        if "image_path" not in category_cols:
            con.execute("ALTER TABLE categories ADD COLUMN image_path TEXT")

        if "photo_path" not in product_cols:
            con.execute("ALTER TABLE products ADD COLUMN photo_path TEXT")

        con.commit()


def ensure_order_columns():
    with connect() as con:
        cols = [r["name"] for r in con.execute("PRAGMA table_info(orders)").fetchall()]
        migrations = {
            "status": "ALTER TABLE orders ADD COLUMN status TEXT DEFAULT 'new'",
            "comment": "ALTER TABLE orders ADD COLUMN comment TEXT",
            "delivery_method": "ALTER TABLE orders ADD COLUMN delivery_method TEXT",
            "delivery_price": "ALTER TABLE orders ADD COLUMN delivery_price INTEGER DEFAULT 0",
            "pickup_point": "ALTER TABLE orders ADD COLUMN pickup_point TEXT",
            "mcd_station": "ALTER TABLE orders ADD COLUMN mcd_station TEXT",
            "delivery_address": "ALTER TABLE orders ADD COLUMN delivery_address TEXT",
            "delivery_date": "ALTER TABLE orders ADD COLUMN delivery_date TEXT",
            "date_surcharge": "ALTER TABLE orders ADD COLUMN date_surcharge INTEGER DEFAULT 0",
            "subtotal": "ALTER TABLE orders ADD COLUMN subtotal INTEGER DEFAULT 0",
            "bonus_used": "ALTER TABLE orders ADD COLUMN bonus_used INTEGER DEFAULT 0",
            "bonus_earned": "ALTER TABLE orders ADD COLUMN bonus_earned INTEGER DEFAULT 0",
            "promo_code": "ALTER TABLE orders ADD COLUMN promo_code TEXT",
            "promo_percent": "ALTER TABLE orders ADD COLUMN promo_percent INTEGER DEFAULT 0",
            "promo_discount": "ALTER TABLE orders ADD COLUMN promo_discount INTEGER DEFAULT 0",
            "referrer_id": "ALTER TABLE orders ADD COLUMN referrer_id INTEGER DEFAULT 0",
            "referral_reward": "ALTER TABLE orders ADD COLUMN referral_reward INTEGER DEFAULT 0",
        }
        for column, sql in migrations.items():
            if column not in cols:
                con.execute(sql)
        con.commit()



def normalize_promocode(value: str | None) -> str:
    code = str(value or "").strip().upper()
    code = re.sub(r"[^A-ZА-ЯЁ0-9_-]", "", code)
    return code[:32]


def ensure_promocode_tables():
    with connect() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS promocodes (
                code TEXT PRIMARY KEY,
                percent INTEGER NOT NULL,
                usage_limit INTEGER NOT NULL DEFAULT 0,
                used_count INTEGER NOT NULL DEFAULT 0,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        promo_cols = [r["name"] for r in con.execute("PRAGMA table_info(promocodes)").fetchall()]
        promo_migrations = {
            "usage_limit": "ALTER TABLE promocodes ADD COLUMN usage_limit INTEGER NOT NULL DEFAULT 0",
            "used_count": "ALTER TABLE promocodes ADD COLUMN used_count INTEGER NOT NULL DEFAULT 0",
        }

        for column, sql in promo_migrations.items():
            if column not in promo_cols:
                con.execute(sql)

        cols = [r["name"] for r in con.execute("PRAGMA table_info(orders)").fetchall()]
        migrations = {
            "promo_code": "ALTER TABLE orders ADD COLUMN promo_code TEXT",
            "promo_percent": "ALTER TABLE orders ADD COLUMN promo_percent INTEGER DEFAULT 0",
            "promo_discount": "ALTER TABLE orders ADD COLUMN promo_discount INTEGER DEFAULT 0",
        }

        for column, sql in migrations.items():
            if column not in cols:
                con.execute(sql)

        con.commit()


def get_active_promocode(con, code: str | None):
    code = normalize_promocode(code)

    if not code:
        return None

    cleanup_expired_promocodes(con)

    return con.execute(
        """
        SELECT *
        FROM promocodes
        WHERE code = ?
          AND active = 1
          AND (usage_limit = 0 OR used_count < usage_limit)
        """,
        (code,)
    ).fetchone()



def cleanup_expired_promocodes(con):
    con.execute(
        """
        DELETE FROM promocodes
        WHERE active = 0
           OR (usage_limit > 0 AND used_count >= usage_limit)
        """
    )


def increment_promocode_usage(con, code: str | None):
    code = normalize_promocode(code)

    if not code:
        return False

    promo = con.execute(
        """
        SELECT *
        FROM promocodes
        WHERE code = ?
          AND active = 1
          AND (usage_limit = 0 OR used_count < usage_limit)
        """,
        (code,)
    ).fetchone()

    if not promo:
        return False

    new_used_count = int(promo["used_count"] or 0) + 1
    usage_limit = int(promo["usage_limit"] or 0)

    if usage_limit > 0 and new_used_count >= usage_limit:
        con.execute("DELETE FROM promocodes WHERE code = ?", (code,))
    else:
        con.execute(
            "UPDATE promocodes SET used_count = ? WHERE code = ?",
            (new_used_count, code)
        )

    return True


def decrement_promocode_usage(con, code: str | None):
    code = normalize_promocode(code)

    if not code:
        return False

    con.execute(
        "UPDATE promocodes SET used_count = MAX(used_count - 1, 0) WHERE code = ?",
        (code,)
    )
    return True



def ensure_bonus_tables():
    with connect() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS bonus_accounts (
                user_id INTEGER PRIMARY KEY,
                balance INTEGER NOT NULL DEFAULT 0,
                referral_code TEXT UNIQUE,
                referrer_id INTEGER,
                referral_bonus_paid INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        con.execute("""
            CREATE TABLE IF NOT EXISTS bonus_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount INTEGER NOT NULL,
                type TEXT NOT NULL,
                order_id INTEGER,
                note TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        con.execute("""
            CREATE TABLE IF NOT EXISTS admin_targets (
                chat_id INTEGER PRIMARY KEY,
                source TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        con.execute("""
            CREATE TABLE IF NOT EXISTS referral_links (
                invited_user_id INTEGER PRIMARY KEY,
                referrer_id INTEGER NOT NULL,
                referral_code TEXT,
                first_order_id INTEGER,
                reward INTEGER NOT NULL DEFAULT 0,
                paid INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                paid_at TIMESTAMP
            )
        """)

        con.execute("""
            CREATE INDEX IF NOT EXISTS idx_referral_links_referrer
            ON referral_links(referrer_id)
        """)
        con.commit()


def make_referral_code(user_id: int) -> str:
    return f"SYN{int(user_id)}"


def normalize_referral_code(value: str | None) -> str | None:
    if not value:
        return None

    code = str(value).strip()
    if code.startswith("ref_"):
        code = code[4:]

    code = code.upper().replace(" ", "")
    return code or None


def referral_link_referrer_id(con, invited_user_id: int) -> int:
    try:
        row = con.execute(
            "SELECT referrer_id FROM referral_links WHERE invited_user_id = ?",
            (int(invited_user_id),)
        ).fetchone()
        if row and int(row["referrer_id"] or 0) > 0:
            return int(row["referrer_id"])
    except Exception:
        pass
    return 0


def ensure_referral_link(con, invited_user_id: int, referrer_id: int, referral_code: str | None = None):
    invited_user_id = int(invited_user_id)
    referrer_id = int(referrer_id)

    if not invited_user_id or not referrer_id or invited_user_id == referrer_id:
        return None

    con.execute(
        """
        INSERT OR IGNORE INTO referral_links (invited_user_id, referrer_id, referral_code)
        VALUES (?, ?, ?)
        """,
        (invited_user_id, referrer_id, referral_code)
    )

    return con.execute(
        "SELECT * FROM referral_links WHERE invited_user_id = ?",
        (invited_user_id,)
    ).fetchone()


def get_or_create_bonus_account(con, user_id: int, ref_code: str | None = None):
    user_id = int(user_id)
    code = make_referral_code(user_id)

    row = con.execute("SELECT * FROM bonus_accounts WHERE user_id = ?", (user_id,)).fetchone()

    if not row:
        con.execute(
            "INSERT OR IGNORE INTO bonus_accounts (user_id, balance, referral_code) VALUES (?, 0, ?)",
            (user_id, code)
        )
        row = con.execute("SELECT * FROM bonus_accounts WHERE user_id = ?", (user_id,)).fetchone()

    if ref_code and not row["referrer_id"]:
        referrer = con.execute(
            "SELECT user_id FROM bonus_accounts WHERE referral_code = ?",
            (ref_code,)
        ).fetchone()

        referrer_id = None

        if referrer:
            referrer_id = int(referrer["user_id"])
        elif ref_code.startswith("SYN") and ref_code[3:].isdigit():
            referrer_id = int(ref_code[3:])
            if referrer_id != user_id:
                get_or_create_bonus_account(con, referrer_id)

        if referrer_id and referrer_id != user_id:
            con.execute(
                "UPDATE bonus_accounts SET referrer_id = ? WHERE user_id = ? AND referrer_id IS NULL",
                (referrer_id, user_id)
            )
            ensure_referral_link(con, user_id, referrer_id, ref_code)
            row = con.execute("SELECT * FROM bonus_accounts WHERE user_id = ?", (user_id,)).fetchone()

    if row and row["referrer_id"]:
        ensure_referral_link(con, user_id, int(row["referrer_id"]), ref_code)

    return row


def add_bonus_transaction(con, user_id: int, amount: int, tx_type: str, order_id: int | None = None, note: str | None = None):
    amount = int(amount or 0)
    if amount == 0:
        return

    con.execute(
        "UPDATE bonus_accounts SET balance = MAX(balance + ?, 0) WHERE user_id = ?",
        (amount, int(user_id))
    )
    con.execute(
        """
        INSERT INTO bonus_transactions (user_id, amount, type, order_id, note)
        VALUES (?, ?, ?, ?, ?)
        """,
        (int(user_id), amount, tx_type, order_id, note)
    )



def register_telegram_user(user: dict):
    if not user or not user.get("id"):
        return None

    user_id = int(user["id"])
    username = user.get("username") or ""
    ref_code = normalize_referral_code(user.get("start_param"))

    with connect() as con:
        con.execute(
            """
            INSERT INTO users (user_id, username)
            VALUES (?, ?)
            ON CONFLICT(user_id)
            DO UPDATE SET username = excluded.username
            """,
            (user_id, username)
        )

        account = get_or_create_bonus_account(con, user_id, ref_code)
        con.commit()
        return account


def account_referrer_id(account) -> int:
    if not account:
        return 0
    try:
        return int(account["referrer_id"] or 0)
    except Exception:
        return 0


def referral_link_for(code: str) -> str:
    # Самый надёжный вариант: сначала открывается бот с /start ref_CODE.
    # Бот фиксирует referrer_id в базе, затем даёт кнопку открытия Mini App.
    # Direct startapp на части клиентов не передаёт start_param стабильно.
    if BOT_USERNAME:
        return f"https://t.me/{BOT_USERNAME}?start=ref_{code}"

    return f"ref_{code}"


def app_referral_link_for(code: str) -> str:
    # Дополнительная прямая ссылка в Mini App. Оставлена как запасная,
    # но основной referral_link теперь специально идёт через /start.
    if BOT_USERNAME and MINI_APP_NAME:
        return f"https://t.me/{BOT_USERNAME}/{MINI_APP_NAME}?startapp=ref_{code}"

    if BOT_USERNAME:
        return f"https://t.me/{BOT_USERNAME}?startapp=ref_{code}"

    return f"ref_{code}"


def delivery_label(value: str | None):
    return {
        "pickup": "Самовывоз",
        "mcd": "МЦД-3",
        "moscow": "По Москве",
    }.get(value or "", value or "не указан")


def parse_delivery_date(value: str | None):
    try:
        selected_date = datetime.strptime(str(value or ""), "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Выберите корректную дату получения")

    today = datetime.now(MOSCOW_TIMEZONE).date()
    last_available_date = today + timedelta(days=6)

    if selected_date < today or selected_date > last_available_date:
        raise HTTPException(status_code=400, detail="Выбранная дата уже недоступна. Обновите корзину.")

    return selected_date.isoformat(), 100 if selected_date == today else 0


def display_delivery_date(value: str | None):
    try:
        return datetime.strptime(str(value or ""), "%Y-%m-%d").strftime("%d.%m.%Y")
    except ValueError:
        return str(value or "")


def order_delivery_lines(order):
    lines = [
        "",
        "<b>Получение:</b>",
        f"Способ: {delivery_label(order['delivery_method'])}",
        f"Стоимость получения: {int(order['delivery_price'] or 0)} ₽",
    ]

    if order["pickup_point"]:
        lines.append(f"Пункт самовывоза: {order['pickup_point']}")
    if order["mcd_station"]:
        lines.append(f"Станция МЦД-3: {order['mcd_station']}")
    if order["delivery_address"]:
        if order["delivery_method"] == "moscow":
            lines.append(f"Ближайшая станция метро: {order['delivery_address']}")
        else:
            lines.append(f"Адрес/город: {order['delivery_address']}")
    if order["delivery_date"]:
        lines.append(f"Дата получения: {display_delivery_date(order['delivery_date'])}")
    if int(order["date_surcharge"] or 0) > 0:
        lines.append(f"День-в-день: +{int(order['date_surcharge'])} ₽")

    return lines


def build_buyer_order_lines(order, items):
    lines = [
        "<b>Спасибо за заказ!</b>",
        f"<b>Заказ №{order['id']} успешно оформлен</b>",
        "",
        "<b>Что заказано:</b>",
    ]

    for item in items:
        label = item['name']
        if item['variant']:
            label = f"{label} — {item['variant']}"
        lines.append(f"• {label} x{item['quantity']} — {item['price'] * item['quantity']} ₽")

    if int(order["promo_discount"] or 0) > 0:
        lines.append(
            f"• Промокод {order['promo_code']}: −{int(order['promo_discount'] or 0)} ₽ "
            f"({int(order['promo_percent'] or 0)}%)"
        )

    if int(order["bonus_used"] or 0) > 0:
        lines.append(f"• Списано баллов: −{int(order['bonus_used'] or 0)} ₽")

    lines.extend([
        "",
        f"<b>Сумма заказа:</b> {int(order['total'] or 0)} ₽",
    ])

    if int(order["bonus_earned"] or 0) > 0:
        lines.append(f"<b>Начислено бонусов:</b> +{int(order['bonus_earned'] or 0)}")

    if order['delivery_method']:
        lines.append(f"<b>Способ получения:</b> {delivery_label(order['delivery_method'])}")
    if order['pickup_point']:
        lines.append(f"<b>Пункт самовывоза:</b> {order['pickup_point']}")
    if order['mcd_station']:
        lines.append(f"<b>Станция МЦД-3:</b> {order['mcd_station']}")
    if order['delivery_address']:
        if order['delivery_method'] == "moscow":
            lines.append(f"<b>Ближайшая станция метро:</b> {order['delivery_address']}")
        else:
            lines.append(f"<b>Адрес/город:</b> {order['delivery_address']}")
    if order['delivery_date']:
        lines.append(f"<b>Дата получения:</b> {display_delivery_date(order['delivery_date'])}")
    if int(order['date_surcharge'] or 0) > 0:
        lines.append(f"<b>День-в-день:</b> +{int(order['date_surcharge'])} ₽")

    text = "\n".join(lines)

    # Telegram photo caption limit is 1024 chars.
    # Отправляем только одно сообщение с картинкой, поэтому аккуратно укорачиваем caption, если заказ слишком большой.
    if len(text) > 1000:
        text = text[:980].rstrip() + "\n…"

    return text


def notify_buyer_order_created(order_id: int):
    if not BOT_TOKEN:
        return

    with connect() as con:
        order = con.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
        items = con.execute("SELECT * FROM order_items WHERE order_id = ? ORDER BY id", (order_id,)).fetchall()

    if not order:
        return

    details_text = build_buyer_order_lines(order, items)

    try:
        tg_api_multipart(
            "sendPhoto",
            {
                "chat_id": order["user_id"],
                "caption": details_text,
                "parse_mode": "HTML",
            },
            "photo",
            THANKS_ORDER_IMAGE,
            "image/png",
        )
    except Exception:
        # Если картинка не отправилась, отправляем одно текстовое сообщение с деталями заказа.
        try:
            tg_api("sendMessage", {
                "chat_id": order["user_id"],
                "text": details_text,
                "parse_mode": "HTML",
            })
        except Exception:
            pass


def is_admin_identity(user_id: int, username: str | None = None) -> bool:
    if int(user_id) in ADMINS:
        return True

    # Безопаснее: username-админка отключена по умолчанию.
    # Включать только временно через ALLOW_USERNAME_ADMINS=1.
    if ALLOW_USERNAME_ADMINS and username and username.lower().lstrip("@") in ADMIN_USERNAMES:
        return True

    return False


def remember_admin_target(user_id: int, username: str | None = None):
    if not is_admin_identity(user_id, username):
        return

    with connect() as con:
        con.execute(
            "INSERT OR IGNORE INTO admin_targets (chat_id, source) VALUES (?, ?)",
            (int(user_id), "admin_private")
        )
        con.commit()


def admin_notification_targets():
    targets = []

    for admin_id in ADMINS:
        if int(admin_id) not in targets:
            targets.append(int(admin_id))

    if ORDER_GROUP_ID and int(ORDER_GROUP_ID) not in targets:
        targets.append(int(ORDER_GROUP_ID))

    try:
        with connect() as con:
            rows = con.execute("SELECT chat_id FROM admin_targets ORDER BY created_at DESC").fetchall()
            for row in rows:
                chat_id = int(row["chat_id"])
                if chat_id not in targets:
                    targets.append(chat_id)
    except Exception:
        pass

    return targets

def notify_admins(order_id: int):
    if not BOT_TOKEN:
        return {"ok": False, "reason": "BOT_TOKEN is empty", "sent": [], "failed": []}

    with connect() as con:
        order = con.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
        items = con.execute("SELECT * FROM order_items WHERE order_id = ?", (order_id,)).fetchall()

    if not order:
        return {"ok": False, "reason": "Order not found", "sent": [], "failed": []}

    username = f"@{order['username']}" if order["username"] else "без username"

    lines = [
        f"<b>Новый заказ №{order['id']}</b>",
        f"Клиент: {username}",
        f"Telegram ID: <code>{order['user_id']}</code>",
        f"Телефон: {order['phone'] or 'не указан'}",
        *order_delivery_lines(order),
        "",
        "<b>Товары:</b>",
    ]

    for item in items:
        label = item['name']
        if item['variant']:
            label = f"{label} — {item['variant']}"
        lines.append(f"• {label} x{item['quantity']} — {item['price'] * item['quantity']} ₽")

    if int(order["promo_discount"] or 0) > 0:
        lines.append(f"\nПромокод: {order['promo_code']} −{int(order['promo_discount'] or 0)} ₽ ({int(order['promo_percent'] or 0)}%)")

    if int(order["bonus_used"] or 0) > 0:
        lines.append(f"Бонусы списаны: −{int(order['bonus_used'] or 0)} ₽")

    lines.append(f"\n<b>Итого:</b> {order['total']} ₽")

    if order["comment"]:
        lines.append(f"\nКомментарий: {order['comment']}")

    keyboard = {
        "inline_keyboard": [
            [
                {"text": "✅ Подтвердить", "callback_data": f"web_confirm_order:{order_id}"},
                {"text": "❌ Отменить", "callback_data": f"web_cancel_order:{order_id}"}
            ],
            [
                {"text": "💬 Написать клиенту", "url": f"tg://user?id={order['user_id']}"}
            ]
        ]
    }

    payload = {
        "text": "\n".join(lines),
        "parse_mode": "HTML",
        "reply_markup": json.dumps(keyboard, ensure_ascii=False)
    }

    sent = []
    failed = []

    for chat_id in admin_notification_targets():
        try:
            response = tg_api("sendMessage", {"chat_id": chat_id, **payload})
            if response and response.get("ok"):
                sent.append(chat_id)
            else:
                failed.append({"chat_id": chat_id, "error": response})
        except Exception as e:
            failed.append({"chat_id": chat_id, "error": str(e)})

    try:
        with connect() as con:
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS notification_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id INTEGER,
                    sent TEXT,
                    failed TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            con.execute(
                "INSERT INTO notification_log (order_id, sent, failed) VALUES (?, ?, ?)",
                (order_id, json.dumps(sent, ensure_ascii=False), json.dumps(failed, ensure_ascii=False))
            )
            con.commit()
    except Exception:
        pass

    return {"ok": bool(sent), "sent": sent, "failed": failed}


def run_order_notifications_background(order_id: int):
    # Отправка сообщений в Telegram не должна тормозить оформление заказа в Mini App.
    try:
        notify_admins(order_id)
    except Exception:
        pass

    try:
        notify_buyer_order_created(order_id)
    except Exception:
        pass


class AddCartRequest(BaseModel):
    product_id: int
    quantity: int = 1
    variant: str | None = None

class UpdateCartRequest(BaseModel):
    product_id: int
    quantity: int
    variant: str | None = None

class RemoveCartRequest(BaseModel):
    product_id: int
    variant: str | None = None

class CreateOrderRequest(BaseModel):
    phone: str
    bonus_to_use: int = 0
    promo_code: str | None = None
    comment: str | None = None
    delivery_method: str | None = None
    delivery_price: int = 0
    pickup_point: str | None = None
    mcd_station: str | None = None
    delivery_address: str | None = None
    delivery_date: str | None = None

class CheckPromocodeRequest(BaseModel):
    code: str
    delivery_method: str | None = None
    delivery_date: str | None = None

@app.on_event("startup")
def startup():
    init_db()
    ensure_image_storage_columns()
    ensure_order_columns()
    ensure_bonus_tables()
    ensure_promocode_tables()

    try:
        with connect() as con:
            con.execute("PRAGMA journal_mode=WAL")
            con.commit()
    except Exception as e:
        logging.warning("SQLite WAL setup failed: %s", e)

@app.get("/api/health")
def health():
    return {"ok": True}

@app.get("/api/me")
def me(request: Request, x_telegram_init_data: str | None = Header(default=None)):
    user = get_user_from_request(request, x_telegram_init_data)

    with connect() as con:
        account = get_or_create_bonus_account(con, int(user["id"]), normalize_referral_code(user.get("start_param")))
        con.commit()

    return {
        "id": user.get("id"),
        "username": user.get("username"),
        "first_name": user.get("first_name"),
        "referral_code": account["referral_code"] if account else None,
        "referrer_id": account["referrer_id"] if account else None,
    }


@app.post("/api/register")
def register_from_app(request: Request, x_telegram_init_data: str | None = Header(default=None)):
    user = get_user_from_request(request, x_telegram_init_data)

    with connect() as con:
        account = get_or_create_bonus_account(con, int(user["id"]), normalize_referral_code(user.get("start_param")))
        con.commit()

    return {
        "ok": True,
        "id": user.get("id"),
        "username": user.get("username"),
        "start_param": user.get("start_param"),
        "referral_code": account["referral_code"] if account else None,
        "referrer_id": account["referrer_id"] if account else None,
    }


@app.get("/api/bonus")
def bonus_info(request: Request, x_telegram_init_data: str | None = Header(default=None)):
    user = get_user_from_request(request, x_telegram_init_data)
    user_id = int(user["id"])
    ref_code = normalize_referral_code(user.get("start_param"))

    with connect() as con:
        account = get_or_create_bonus_account(con, user_id, ref_code)
        tx_rows = con.execute(
            """
            SELECT amount, type, order_id, note, created_at
            FROM bonus_transactions
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT 20
            """,
            (user_id,)
        ).fetchall()
        con.commit()

    code = account["referral_code"] or make_referral_code(user_id)

    return {
        "balance": int(account["balance"] or 0),
        "referral_code": code,
        "referral_link": referral_link_for(code),
        "app_referral_link": app_referral_link_for(code),
        "cashback_percent": 2,
        "max_redeem_percent": 40,
        "referral_reward_under_2000": 100,
        "referral_reward_from_2000": 150,
        "transactions": [dict(row) for row in tx_rows],
    }

@app.get("/api/tg-file")
def tg_file(file_id: str):
    if not BOT_TOKEN:
        raise HTTPException(status_code=500, detail="BOT_TOKEN is empty")

    if not file_id_is_public_image(file_id):
        raise HTTPException(status_code=404, detail="File not found")

    data = tg_api("getFile", {"file_id": file_id})
    token_for_file = BOT_TOKEN

    if (not data or not data.get("ok")) and OLD_BOT_TOKEN:
        old_url = f"https://api.telegram.org/bot{OLD_BOT_TOKEN}/getFile"
        payload = urllib.parse.urlencode({"file_id": file_id}).encode("utf-8")
        req = urllib.request.Request(old_url, data=payload, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                data = json.loads(response.read().decode("utf-8"))
            token_for_file = OLD_BOT_TOKEN
        except Exception:
            data = None

    if not data or not data.get("ok"):
        raise HTTPException(status_code=404, detail="File not found")

    file_path = data["result"]["file_path"]
    url = f"https://api.telegram.org/file/bot{token_for_file}/{file_path}"

    return RedirectResponse(url)

@app.get("/api/order-thanks-image")
def order_thanks_image():
    if not THANKS_ORDER_IMAGE.exists():
        raise HTTPException(status_code=404, detail="Thanks image not found")
    return FileResponse(THANKS_ORDER_IMAGE, media_type="image/png")

@app.get("/api/debug/status")
def debug_status(request: Request, x_telegram_init_data: str | None = Header(default=None)):
    if not debug_allowed(request, x_telegram_init_data):
        raise HTTPException(status_code=403, detail="Forbidden")

    with connect() as con:
        categories_total = con.execute("SELECT COUNT(*) FROM categories").fetchone()[0]
        categories_with_images = con.execute("SELECT COUNT(*) FROM categories WHERE image_id IS NOT NULL AND image_id != ''").fetchone()[0]
        products_total = con.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        products_with_images = con.execute("SELECT COUNT(*) FROM products WHERE photo_id IS NOT NULL AND photo_id != ''").fetchone()[0]
        users_total = con.execute("SELECT COUNT(*) FROM users").fetchone()[0]

    return {
        "bot_token_set": bool(BOT_TOKEN),
        "admins": ADMINS,
        "order_group_id": ORDER_GROUP_ID,
        "admin_targets": admin_notification_targets(),
        "bot_username": BOT_USERNAME,
        "mini_app_name": MINI_APP_NAME,
        "db_path": str(DB_PATH),
        "categories_total": categories_total,
        "categories_with_images": categories_with_images,
        "products_total": products_total,
        "products_with_images": products_with_images,
        "users_total": users_total,
    }



@app.get("/api/debug/uploads")
def debug_uploads(request: Request, x_telegram_init_data: str | None = Header(default=None)):
    if not debug_allowed(request, x_telegram_init_data):
        raise HTTPException(status_code=403, detail="Forbidden")

    ensure_upload_dir()
    files = []
    try:
        for path in UPLOAD_DIR.glob("*"):
            if path.is_file():
                files.append({
                    "name": path.name,
                    "size": path.stat().st_size,
                    "url": f"/uploads/{path.name}",
                })
    except Exception as e:
        return {"upload_dir": str(UPLOAD_DIR), "error": str(e), "files": []}

    return {
        "upload_dir": str(UPLOAD_DIR),
        "files_count": len(files),
        "files": files[:30],
        "mount": "/uploads",
    }


@app.get("/api/debug/images")
def debug_images(request: Request, x_telegram_init_data: str | None = Header(default=None)):
    if not debug_allowed(request, x_telegram_init_data):
        raise HTTPException(status_code=403, detail="Forbidden")

    return image_storage_status(connect)


@app.get("/api/debug/notifications")
def debug_notifications(request: Request, x_telegram_init_data: str | None = Header(default=None)):
    if not debug_allowed(request, x_telegram_init_data):
        raise HTTPException(status_code=403, detail="Forbidden")

    with connect() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS notification_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER,
                sent TEXT,
                failed TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        rows = con.execute(
            "SELECT * FROM notification_log ORDER BY id DESC LIMIT 20"
        ).fetchall()

    return {
        "targets": admin_notification_targets(),
        "logs": [dict(row) for row in rows],
    }


@app.get("/api/debug/referral/{user_id}")
def debug_referral(user_id: int, request: Request, x_telegram_init_data: str | None = Header(default=None)):
    if not debug_allowed(request, x_telegram_init_data):
        raise HTTPException(status_code=403, detail="Forbidden")

    with connect() as con:
        account = con.execute("SELECT * FROM bonus_accounts WHERE user_id = ?", (user_id,)).fetchone()
        orders = con.execute(
            """
            SELECT id, status, total, referrer_id, referral_reward, bonus_earned, created_at
            FROM orders
            WHERE user_id = ? OR referrer_id = ?
            ORDER BY id DESC
            LIMIT 20
            """,
            (user_id, user_id)
        ).fetchall()
        tx = con.execute(
            """
            SELECT id, user_id, amount, type, order_id, note, created_at
            FROM bonus_transactions
            WHERE user_id = ? OR note LIKE ?
            ORDER BY id DESC
            LIMIT 20
            """,
            (user_id, f"%{user_id}%")
        ).fetchall()

        referral_links = con.execute(
            """
            SELECT *
            FROM referral_links
            WHERE invited_user_id = ? OR referrer_id = ?
            ORDER BY created_at DESC
            LIMIT 50
            """,
            (user_id, user_id)
        ).fetchall()

    return {
        "account": dict(account) if account else None,
        "orders": [dict(row) for row in orders],
        "transactions": [dict(row) for row in tx],
        "referral_links": [dict(row) for row in referral_links],
    }


@app.get("/api/categories")
def categories():
    with connect() as con:
        rows = con.execute("SELECT * FROM categories ORDER BY id").fetchall()
        return [category_dict(r) for r in rows]

@app.get("/api/products")
def products(category_id: int, search: str = "", sort: str = "default", limit: int = 100, offset: int = 0):
    limit = min(max(limit, 1), 100)
    search = search.strip()

    order_by = "id DESC"
    if sort == "cheap":
        order_by = "price ASC"
    elif sort == "expensive":
        order_by = "price DESC"

    query = """
        SELECT *
        FROM products
        WHERE category_id = ?
          AND quantity > 0
    """
    params = [category_id]

    if search:
        query += " AND (LOWER(name) LIKE ? OR LOWER(description) LIKE ?)"
        q = f"%{search.lower()}%"
        params.extend([q, q])

    query += f" ORDER BY {order_by} LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    with connect() as con:
        rows = con.execute(query, params).fetchall()
        return [product_dict(r) for r in rows]

@app.get("/api/product/{product_id}")
def product_detail(product_id: int):
    with connect() as con:
        row = con.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Товар не найден")

    return product_dict(row)

@app.post("/api/cart/add")
def cart_add(data: AddCartRequest, request: Request, x_telegram_init_data: str | None = Header(default=None)):
    user = get_user_from_request(request, x_telegram_init_data)
    user_id = int(user["id"])
    add_qty = min(max(int(data.quantity), 1), MAX_CART_QUANTITY)

    with connect() as con:
        product = con.execute("SELECT * FROM products WHERE id = ?", (data.product_id,)).fetchone()

        if not product or product["quantity"] <= 0:
            raise HTTPException(status_code=400, detail="Товара нет в наличии")

        variants = parse_variant_stock_options(product["variant_options"], fallback_stock=product["quantity"])
        available_variants = [
            item["name"]
            for item in variants
            if int(item["stock"] or 0) > 0
        ]
        variant = (data.variant or "").strip()

        if variants:
            if not variant:
                raise HTTPException(status_code=400, detail="Выберите вариант товара")
            if variant not in available_variants:
                raise HTTPException(status_code=400, detail="Выбран неверный вариант товара или вкус закончился")
            available_stock = variant_stock_for(product["variant_options"], variant, fallback_stock=product["quantity"])
        else:
            variant = ""
            available_stock = int(product["quantity"] or 0)

        row = con.execute(
            "SELECT quantity FROM cart WHERE user_id = ? AND product_id = ? AND variant = ?",
            (user_id, data.product_id, variant)
        ).fetchone()

        current_qty = row["quantity"] if row else 0

        if current_qty + add_qty > available_stock:
            raise HTTPException(status_code=400, detail="Недостаточно выбранного вкуса")

        con.execute("""
            INSERT INTO cart (user_id, product_id, variant, quantity)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, product_id, variant)
            DO UPDATE SET quantity = quantity + excluded.quantity
        """, (user_id, data.product_id, variant, add_qty))
        con.commit()

    return {"ok": True}

@app.post("/api/cart/update")
def cart_update(data: UpdateCartRequest, request: Request, x_telegram_init_data: str | None = Header(default=None)):
    user = get_user_from_request(request, x_telegram_init_data)
    user_id = int(user["id"])
    qty = min(max(int(data.quantity), 0), MAX_CART_QUANTITY)

    with connect() as con:
        product = con.execute("SELECT * FROM products WHERE id = ?", (data.product_id,)).fetchone()
        variant = (data.variant or "").strip()

        if qty == 0:
            con.execute(
                "DELETE FROM cart WHERE user_id = ? AND product_id = ? AND variant = ?",
                (user_id, data.product_id, variant)
            )
            con.commit()
            return {"ok": True}

        if not product or product["quantity"] <= 0:
            raise HTTPException(status_code=400, detail="Товара нет в наличии")

        variants = parse_variant_stock_options(product["variant_options"], fallback_stock=product["quantity"])
        available_variants = [
            item["name"]
            for item in variants
            if int(item["stock"] or 0) > 0
        ]

        if variants:
            if not variant:
                raise HTTPException(status_code=400, detail="Выберите вариант товара")
            if variant not in available_variants:
                raise HTTPException(status_code=400, detail="Выбран неверный вариант товара или вкус закончился")
            available_stock = variant_stock_for(product["variant_options"], variant, fallback_stock=product["quantity"])
        else:
            variant = ""
            available_stock = int(product["quantity"] or 0)

        if qty > available_stock:
            raise HTTPException(status_code=400, detail="Недостаточно выбранного вкуса")

        con.execute("""
            INSERT INTO cart (user_id, product_id, variant, quantity)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, product_id, variant)
            DO UPDATE SET quantity = excluded.quantity
        """, (user_id, data.product_id, variant, qty))
        con.commit()

    return {"ok": True}

@app.post("/api/cart/remove")
def cart_remove(data: RemoveCartRequest, request: Request, x_telegram_init_data: str | None = Header(default=None)):
    user = get_user_from_request(request, x_telegram_init_data)
    user_id = int(user["id"])

    with connect() as con:
        con.execute("DELETE FROM cart WHERE user_id = ? AND product_id = ? AND variant = ?", (user_id, data.product_id, (data.variant or "").strip()))
        con.commit()

    return {"ok": True}

@app.post("/api/promocode/check")
def check_promocode(data: CheckPromocodeRequest, request: Request, x_telegram_init_data: str | None = Header(default=None)):
    user = get_user_from_request(request, x_telegram_init_data)
    user_id = int(user["id"])

    with connect() as con:
        promo = get_active_promocode(con, data.code)

        if not promo:
            raise HTTPException(status_code=404, detail="Промокод не найден или отключён")

        rows = con.execute("""
            SELECT c.quantity, p.price
            FROM cart c
            JOIN products p ON p.id = c.product_id
            WHERE c.user_id = ?
        """, (user_id,)).fetchall()

        subtotal = sum(int(row["price"] or 0) * int(row["quantity"] or 0) for row in rows)

    if subtotal <= 0:
        raise HTTPException(status_code=400, detail="Корзина пустая")

    delivery_price = 300 if data.delivery_method == "moscow" else 100 if data.delivery_method == "mcd" else 0
    _, date_surcharge = parse_delivery_date(data.delivery_date)
    amount_for_discount = subtotal + delivery_price + date_surcharge
    percent = max(1, min(int(promo["percent"] or 0), 100))
    discount = amount_for_discount * percent // 100

    return {
        "ok": True,
        "code": promo["code"],
        "percent": percent,
        "discount": discount,
        "subtotal": subtotal,
        "delivery_price": delivery_price,
        "date_surcharge": date_surcharge,
        "amount_for_discount": amount_for_discount,
        "usage_limit": int(promo["usage_limit"] or 0),
        "used_count": int(promo["used_count"] or 0),
        "left_count": None if int(promo["usage_limit"] or 0) == 0 else max(int(promo["usage_limit"] or 0) - int(promo["used_count"] or 0), 0),
    }


@app.get("/api/cart")
def cart(request: Request, x_telegram_init_data: str | None = Header(default=None)):
    user = get_user_from_request(request, x_telegram_init_data)
    user_id = int(user["id"])

    with connect() as con:
        rows = con.execute("""
            SELECT
                c.product_id,
                c.variant,
                c.quantity,
                p.id AS db_product_id,
                p.name,
                p.price,
                p.photo_id,
                p.photo_path,
                p.description,
                p.quantity AS stock,
                p.variant_options
            FROM cart c
            LEFT JOIN products p ON p.id = c.product_id
            WHERE c.user_id = ?
        """, (user_id,)).fetchall()

    items = [cart_item_dict(r) for r in rows]
    total = sum(int(i["price"] or 0) * int(i["quantity"] or 0) for i in items)
    unavailable_count = sum(1 for i in items if not i.get("can_checkout", True))

    return {
        "items": items,
        "total": total,
        "count": sum(int(i["quantity"] or 0) for i in items),
        "unavailable_count": unavailable_count,
        "can_checkout": unavailable_count == 0,
    }

@app.post("/api/cart/clear")
def cart_clear(request: Request, x_telegram_init_data: str | None = Header(default=None)):
    user = get_user_from_request(request, x_telegram_init_data)
    user_id = int(user["id"])

    with connect() as con:
        con.execute("DELETE FROM cart WHERE user_id = ?", (user_id,))
        con.commit()

    return {"ok": True}

@app.post("/api/orders")
def create_order(
    data: CreateOrderRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    x_telegram_init_data: str | None = Header(default=None)
):
    try:
        return create_order_internal(data, request, background_tasks, x_telegram_init_data)
    except HTTPException:
        raise
    except Exception as e:
        logging.exception("Order creation failed")
        raise HTTPException(status_code=500, detail=f"Ошибка оформления заказа: {type(e).__name__}")


def create_order_internal(
    data: CreateOrderRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    x_telegram_init_data: str | None = Header(default=None)
):
    user = get_user_from_request(request, x_telegram_init_data)
    user_id = int(user["id"])
    username = clean_text(user.get("username"), 64)

    phone = clean_text(data.phone, 32)
    comment = clean_text(data.comment, MAX_COMMENT_LENGTH)
    pickup_point = clean_text(data.pickup_point, 64)
    mcd_station = clean_text(data.mcd_station, 64)
    delivery_address = clean_text(data.delivery_address, 120)
    delivery_date, date_surcharge = parse_delivery_date(data.delivery_date)

    if len(phone) < 10 or len(phone) > 32:
        raise HTTPException(status_code=400, detail="Введите корректный номер телефона")

    with connect() as con:
        con.execute("BEGIN IMMEDIATE")

        recent_order = con.execute(
            """
            SELECT id
            FROM orders
            WHERE user_id = ?
              AND created_at >= DATETIME('now', '-3 seconds')
            LIMIT 1
            """,
            (user_id,)
        ).fetchone()

        if recent_order:
            con.execute("ROLLBACK")
            raise HTTPException(status_code=429, detail="Заказ уже оформляется. Подождите 3 секунды.")

        cart_rows = con.execute("""
            SELECT c.product_id, c.variant, c.quantity, p.name, p.price, p.quantity AS stock, p.variant_options
            FROM cart c
            JOIN products p ON p.id = c.product_id
            WHERE c.user_id = ?
        """, (user_id,)).fetchall()

        if not cart_rows:
            con.execute("ROLLBACK")
            raise HTTPException(status_code=400, detail="Корзина пустая")

        for item in cart_rows:
            variants = parse_variant_stock_options(item["variant_options"], fallback_stock=item["stock"])

            if variants:
                available_stock = variant_stock_for(item["variant_options"], item["variant"], fallback_stock=item["stock"])
                error_label = f"{item['name']} — {item['variant']}"
            else:
                available_stock = int(item["stock"] or 0)
                error_label = item["name"]

            if int(item["quantity"] or 0) > available_stock:
                con.execute("ROLLBACK")
                raise HTTPException(status_code=400, detail=f"Недостаточно товара: {error_label}")

        if data.delivery_method not in {"pickup", "mcd", "moscow"}:
            con.execute("ROLLBACK")
            raise HTTPException(status_code=400, detail="Выберите способ получения")

        if data.delivery_method == "pickup" and pickup_point not in PICKUP_POINTS:
            con.execute("ROLLBACK")
            raise HTTPException(status_code=400, detail="Выберите корректный пункт самовывоза")

        if data.delivery_method == "mcd" and len(mcd_station) < 2:
            con.execute("ROLLBACK")
            raise HTTPException(status_code=400, detail="Введите станцию МЦД-3")

        if data.delivery_method == "moscow" and len(delivery_address) < 2:
            con.execute("ROLLBACK")
            raise HTTPException(status_code=400, detail="Введите ближайшую станцию метро")

        delivery_price = 300 if data.delivery_method == "moscow" else 100 if data.delivery_method == "mcd" else 0
        subtotal = sum(item["price"] * item["quantity"] for item in cart_rows)

        promo_code = normalize_promocode(data.promo_code)
        promo = get_active_promocode(con, promo_code) if promo_code else None

        if promo_code and not promo:
            con.execute("ROLLBACK")
            raise HTTPException(status_code=400, detail="Промокод не найден, отключён или закончился")

        promo_percent = max(1, min(int(promo["percent"] or 0), 100)) if promo else 0
        amount_for_discount = subtotal + delivery_price + date_surcharge
        promo_discount = amount_for_discount * promo_percent // 100 if promo else 0
        promo_code_value = promo["code"] if promo else None

        gross_total = max(amount_for_discount - promo_discount, 0)

        account = get_or_create_bonus_account(
            con,
            user_id,
            normalize_referral_code(user.get("start_param"))
        )
        referrer_id = account_referrer_id(account)

        if referrer_id:
            ensure_referral_link(
                con,
                user_id,
                referrer_id,
                normalize_referral_code(user.get("start_param"))
            )

        balance = int(account["balance"] or 0)
        max_bonus = min(balance, gross_total * 40 // 100)
        bonus_used = min(max(int(data.bonus_to_use or 0), 0), max_bonus)
        total = gross_total - bonus_used
        # Кэшбэк начисляется только после подтверждения заказа админом.
        bonus_earned = 0

        cur = con.execute(
            """
            INSERT INTO orders (
                user_id, username, phone, total, comment, status,
                delivery_method, delivery_price, pickup_point, mcd_station, delivery_address, delivery_date, date_surcharge,
                subtotal, bonus_used, bonus_earned, promo_code, promo_percent, promo_discount, referrer_id, referral_reward
            )
            VALUES (?, ?, ?, ?, ?, 'new', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id, username, phone, total, comment,
                data.delivery_method, delivery_price, pickup_point if data.delivery_method == "pickup" else None,
                mcd_station if data.delivery_method == "mcd" else None,
                delivery_address if data.delivery_method == "moscow" else None,
                delivery_date, date_surcharge,
                subtotal, bonus_used, bonus_earned, promo_code_value, promo_percent, promo_discount, referrer_id, 0
            )
        )
        order_id = cur.lastrowid

        if bonus_used > 0:
            add_bonus_transaction(
                con,
                user_id,
                -bonus_used,
                "spend",
                order_id,
                "Списание баллов при оформлении заказа"
            )

        for item in cart_rows:
            con.execute("""
                INSERT INTO order_items (order_id, product_id, name, variant, price, quantity)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (order_id, item["product_id"], item["name"], item["variant"], item["price"], item["quantity"]))

        con.execute("DELETE FROM cart WHERE user_id = ?", (user_id,))
        con.commit()

    background_tasks.add_task(run_order_notifications_background, order_id)

    return {
        "ok": True,
        "order_id": order_id,
        "total": total,
        "promo_code": promo_code_value,
        "promo_discount": promo_discount,
        "delivery_date": delivery_date,
        "date_surcharge": date_surcharge,
        "promo_applies_to": "items_and_delivery",
        "notifications": "queued"
    }

@app.get("/api/orders/my")
def my_orders(request: Request, x_telegram_init_data: str | None = Header(default=None)):
    user = get_user_from_request(request, x_telegram_init_data)
    user_id = int(user["id"])

    with connect() as con:
        rows = con.execute("""
            SELECT *
            FROM orders
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT 50
        """, (user_id,)).fetchall()

    return [dict(r) for r in rows]


# ===== Frontend static serving for Dockhost =====

FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"

if (FRONTEND_DIST / "assets").exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

@app.get("/")
def serve_frontend_index():
    index_file = FRONTEND_DIST / "index.html"
    if index_file.exists():
        return FileResponse(index_file, headers={"Cache-Control": "no-store, max-age=0"})
    return {"message": "Frontend not built"}

@app.get("/{full_path:path}")
def serve_frontend_fallback(full_path: str):
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Not Found")

    requested_file = FRONTEND_DIST / full_path
    if requested_file.exists() and requested_file.is_file():
        return FileResponse(requested_file, headers={"Cache-Control": "public, max-age=0"})

    index_file = FRONTEND_DIST / "index.html"
    if index_file.exists():
        return FileResponse(index_file, headers={"Cache-Control": "no-store, max-age=0"})

    return {"message": "Frontend not built"}
