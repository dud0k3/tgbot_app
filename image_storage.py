import json
import os
import shutil
import posixpath
import urllib.parse
import urllib.request
from pathlib import Path
from uuid import uuid4

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "/data/uploads")).resolve()
PUBLIC_UPLOAD_PREFIX = "/uploads"

try:
    _legacy_upload_dir = Path(__file__).resolve().parent / "data" / "uploads"
    if not os.getenv("UPLOAD_DIR") and _legacy_upload_dir.exists():
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        for _src in _legacy_upload_dir.glob("*"):
            _dst = UPLOAD_DIR / _src.name
            if _src.is_file() and not _dst.exists():
                shutil.copy2(_src, _dst)
except Exception:
    pass
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


def ensure_upload_dir():
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def public_upload_path(filename: str) -> str:
    return f"{PUBLIC_UPLOAD_PREFIX}/{filename}"


def local_filesystem_path(public_path: str) -> Path:
    filename = str(public_path or "").replace(PUBLIC_UPLOAD_PREFIX + "/", "", 1).strip("/")
    return UPLOAD_DIR / filename


def safe_extension(file_path: str | None) -> str:
    suffix = Path(str(file_path or "")).suffix.lower()

    if suffix not in ALLOWED_EXTENSIONS:
        return ".jpg"

    return suffix


def make_image_filename(prefix: str, file_path: str | None = None) -> str:
    prefix = "".join(ch for ch in str(prefix or "image").lower() if ch.isalnum() or ch in {"_", "-"}).strip("-_") or "image"
    return f"{prefix}_{uuid4().hex}{safe_extension(file_path)}"


async def save_telegram_photo(bot, file_id: str, prefix: str = "image") -> str | None:
    if not file_id:
        return None

    ensure_upload_dir()

    file = await bot.get_file(file_id)
    filename = make_image_filename(prefix, file.file_path)
    target = UPLOAD_DIR / filename

    await bot.download_file(file.file_path, destination=target)

    return public_upload_path(filename)


def telegram_get_file(token: str, file_id: str) -> dict | None:
    if not token or not file_id:
        return None

    url = f"https://api.telegram.org/bot{token}/getFile"
    payload = urllib.parse.urlencode({"file_id": file_id}).encode("utf-8")
    request = urllib.request.Request(url, data=payload, method="POST")

    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            data = json.loads(response.read().decode("utf-8"))

        if data.get("ok"):
            return data["result"]
    except Exception:
        return None

    return None


def download_telegram_file_by_token(token: str, file_id: str, prefix: str = "image") -> str | None:
    info = telegram_get_file(token, file_id)

    if not info:
        return None

    file_path = info.get("file_path")
    if not file_path:
        return None

    ensure_upload_dir()

    filename = make_image_filename(prefix, file_path)
    target = UPLOAD_DIR / filename
    url = f"https://api.telegram.org/file/bot{token}/{file_path}"

    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            target.write_bytes(response.read())
    except Exception:
        return None

    return public_upload_path(filename)


async def cache_one_telegram_image(bot, file_id: str, prefix: str, old_bot_token: str | None = None) -> str | None:
    if not file_id:
        return None

    # При переносе на нового бота старые file_id чаще всего открываются только старым BOT_TOKEN.
    if old_bot_token:
        saved = download_telegram_file_by_token(old_bot_token, file_id, prefix)
        if saved:
            return saved

    try:
        return await save_telegram_photo(bot, file_id, prefix)
    except Exception:
        return None


def local_image_exists(public_path: str | None) -> bool:
    if not public_path:
        return False

    if not str(public_path).startswith(PUBLIC_UPLOAD_PREFIX + "/"):
        return False

    return local_filesystem_path(public_path).exists()


def image_storage_status(connect_func):
    ensure_upload_dir()

    with connect_func() as con:
        category_cols = [r["name"] for r in con.execute("PRAGMA table_info(categories)").fetchall()]
        product_cols = [r["name"] for r in con.execute("PRAGMA table_info(products)").fetchall()]

        if "image_path" not in category_cols:
            con.execute("ALTER TABLE categories ADD COLUMN image_path TEXT")

        if "photo_path" not in product_cols:
            con.execute("ALTER TABLE products ADD COLUMN photo_path TEXT")

        con.commit()

        categories = con.execute(
            "SELECT id, name, image_id, image_path FROM categories"
        ).fetchall()

        products = con.execute(
            "SELECT id, name, photo_id, photo_path FROM products"
        ).fetchall()

    cat_total = len(categories)
    prod_total = len(products)

    cat_with_file_id = sum(1 for row in categories if row["image_id"])
    prod_with_file_id = sum(1 for row in products if row["photo_id"])

    cat_with_local = sum(1 for row in categories if local_image_exists(row["image_path"]))
    prod_with_local = sum(1 for row in products if local_image_exists(row["photo_path"]))

    cat_missing_local = [
        {"id": row["id"], "name": row["name"], "image_id": bool(row["image_id"]), "image_path": row["image_path"]}
        for row in categories
        if row["image_id"] and not local_image_exists(row["image_path"])
    ]

    prod_missing_local = [
        {"id": row["id"], "name": row["name"], "photo_id": bool(row["photo_id"]), "photo_path": row["photo_path"]}
        for row in products
        if row["photo_id"] and not local_image_exists(row["photo_path"])
    ]

    return {
        "categories_total": cat_total,
        "products_total": prod_total,
        "categories_with_file_id": cat_with_file_id,
        "products_with_file_id": prod_with_file_id,
        "categories_with_local_file": cat_with_local,
        "products_with_local_file": prod_with_local,
        "categories_missing_local": len(cat_missing_local),
        "products_missing_local": len(prod_missing_local),
        "categories_missing_examples": cat_missing_local[:10],
        "products_missing_examples": prod_missing_local[:10],
        "upload_dir": str(UPLOAD_DIR),
    }


async def cache_all_db_images(bot, connect_func, old_bot_token: str | None = None):
    result = {
        "categories_cached": 0,
        "products_cached": 0,
        "categories_failed": 0,
        "products_failed": 0,
        "categories_already_local": 0,
        "products_already_local": 0,
    }

    ensure_upload_dir()

    with connect_func() as con:
        category_cols = [r["name"] for r in con.execute("PRAGMA table_info(categories)").fetchall()]
        product_cols = [r["name"] for r in con.execute("PRAGMA table_info(products)").fetchall()]

        if "image_path" not in category_cols:
            con.execute("ALTER TABLE categories ADD COLUMN image_path TEXT")

        if "photo_path" not in product_cols:
            con.execute("ALTER TABLE products ADD COLUMN photo_path TEXT")

        con.commit()

        categories = con.execute(
            """
            SELECT id, image_id, image_path
            FROM categories
            WHERE image_id IS NOT NULL
              AND image_id != ''
            """
        ).fetchall()

        products = con.execute(
            """
            SELECT id, photo_id, photo_path
            FROM products
            WHERE photo_id IS NOT NULL
              AND photo_id != ''
            """
        ).fetchall()

    for row in categories:
        if local_image_exists(row["image_path"]):
            result["categories_already_local"] += 1
            continue

        saved = await cache_one_telegram_image(bot, row["image_id"], "category", old_bot_token)

        with connect_func() as con:
            if saved:
                con.execute("UPDATE categories SET image_path = ? WHERE id = ?", (saved, int(row["id"])))
                result["categories_cached"] += 1
            else:
                con.execute("UPDATE categories SET image_path = NULL WHERE id = ?", (int(row["id"]),))
                result["categories_failed"] += 1
            con.commit()

    for row in products:
        if local_image_exists(row["photo_path"]):
            result["products_already_local"] += 1
            continue

        saved = await cache_one_telegram_image(bot, row["photo_id"], "product", old_bot_token)

        with connect_func() as con:
            if saved:
                con.execute("UPDATE products SET photo_path = ? WHERE id = ?", (saved, int(row["id"])))
                result["products_cached"] += 1
            else:
                con.execute("UPDATE products SET photo_path = NULL WHERE id = ?", (int(row["id"]),))
                result["products_failed"] += 1
            con.commit()

    return result
