import sqlite3
import re
import json

from config import DB_PATH

def connect():
    con = sqlite3.connect(DB_PATH, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA foreign_keys=ON")
    return con

def init_db():
    with connect() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        con.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                emoji TEXT DEFAULT '',
                image_id TEXT,
                image_path TEXT
            )
        """)

        con.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER,
                name TEXT NOT NULL,
                description TEXT,
                variant_options TEXT,
                price INTEGER NOT NULL,
                quantity INTEGER DEFAULT 0,
                photo_id TEXT,
                photo_path TEXT,
                FOREIGN KEY(category_id) REFERENCES categories(id)
            )
        """)

        con.execute("""
            CREATE TABLE IF NOT EXISTS cart (
                user_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                variant TEXT NOT NULL DEFAULT '',
                quantity INTEGER NOT NULL DEFAULT 1,
                PRIMARY KEY (user_id, product_id, variant)
            )
        """)

        con.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT,
                phone TEXT,
                total INTEGER NOT NULL,
                status TEXT DEFAULT 'new',
                comment TEXT,
                delivery_method TEXT,
                delivery_price INTEGER DEFAULT 0,
                pickup_point TEXT,
                mcd_station TEXT,
                delivery_address TEXT,
                delivery_date TEXT,
                date_surcharge INTEGER DEFAULT 0,
                subtotal INTEGER DEFAULT 0,
                bonus_used INTEGER DEFAULT 0,
                bonus_earned INTEGER DEFAULT 0,
                promo_code TEXT,
                promo_percent INTEGER DEFAULT 0,
                promo_discount INTEGER DEFAULT 0,
                referrer_id INTEGER DEFAULT 0,
                referral_reward INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        con.execute("""
            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                variant TEXT,
                price INTEGER NOT NULL,
                quantity INTEGER NOT NULL
            )
        """)

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
            CREATE TABLE IF NOT EXISTS promocodes (
                code TEXT PRIMARY KEY,
                percent INTEGER NOT NULL,
                usage_limit INTEGER NOT NULL DEFAULT 0,
                used_count INTEGER NOT NULL DEFAULT 0,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)


        try:
            con.execute("ALTER TABLE categories ADD COLUMN emoji TEXT DEFAULT ''")
        except sqlite3.OperationalError:
            pass

        try:
            con.execute("ALTER TABLE categories ADD COLUMN image_id TEXT")
        except sqlite3.OperationalError:
            pass

        try:
            con.execute("ALTER TABLE products ADD COLUMN category_id INTEGER")
        except sqlite3.OperationalError:
            pass

        try:
            con.execute("ALTER TABLE products ADD COLUMN variant_options TEXT")
        except sqlite3.OperationalError:
            pass

        try:
            con.execute("ALTER TABLE orders ADD COLUMN phone TEXT")
        except sqlite3.OperationalError:
            pass

        try:
            con.execute("ALTER TABLE orders ADD COLUMN status TEXT DEFAULT 'new'")
        except sqlite3.OperationalError:
            pass

        try:
            con.execute("ALTER TABLE orders ADD COLUMN comment TEXT")
        except sqlite3.OperationalError:
            pass

        try:
            con.execute("ALTER TABLE orders ADD COLUMN subtotal INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass

        try:
            con.execute("ALTER TABLE orders ADD COLUMN bonus_used INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass

        try:
            con.execute("ALTER TABLE orders ADD COLUMN bonus_earned INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass

        try:
            con.execute("ALTER TABLE orders ADD COLUMN referrer_id INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass

        try:
            con.execute("ALTER TABLE orders ADD COLUMN referral_reward INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass

        try:
            con.execute("ALTER TABLE orders ADD COLUMN promo_code TEXT")
        except sqlite3.OperationalError:
            pass

        try:
            con.execute("ALTER TABLE orders ADD COLUMN promo_percent INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass

        try:
            con.execute("ALTER TABLE orders ADD COLUMN promo_discount INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass

        try:
            con.execute("ALTER TABLE orders ADD COLUMN delivery_date TEXT")
        except sqlite3.OperationalError:
            pass

        try:
            con.execute("ALTER TABLE orders ADD COLUMN date_surcharge INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass

        try:
            con.execute("ALTER TABLE orders ADD COLUMN courier_id INTEGER")
        except sqlite3.OperationalError:
            pass

        try:
            con.execute("ALTER TABLE promocodes ADD COLUMN usage_limit INTEGER NOT NULL DEFAULT 0")
        except sqlite3.OperationalError:
            pass

        try:
            con.execute("ALTER TABLE promocodes ADD COLUMN used_count INTEGER NOT NULL DEFAULT 0")
        except sqlite3.OperationalError:
            pass


        try:
            con.execute("ALTER TABLE order_items ADD COLUMN variant TEXT")
        except sqlite3.OperationalError:
            pass

        cart_cols = [r["name"] for r in con.execute("PRAGMA table_info(cart)").fetchall()]
        if "variant" not in cart_cols:
            con.execute("ALTER TABLE cart RENAME TO cart_old")
            con.execute("""
                CREATE TABLE cart (
                    user_id INTEGER NOT NULL,
                    product_id INTEGER NOT NULL,
                    variant TEXT NOT NULL DEFAULT '',
                    quantity INTEGER NOT NULL DEFAULT 1,
                    PRIMARY KEY (user_id, product_id, variant)
                )
            """)
            con.execute("""
                INSERT INTO cart (user_id, product_id, variant, quantity)
                SELECT user_id, product_id, '', quantity FROM cart_old
            """)
            con.execute("DROP TABLE cart_old")


        con.execute("""
            INSERT OR IGNORE INTO categories (id, name, emoji, image_id)
            VALUES (1, 'Без категории', '', NULL)
        """)
        con.execute("UPDATE products SET category_id = 1 WHERE category_id IS NULL")
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

        con.execute("""
            CREATE TABLE IF NOT EXISTS admin_targets (
                chat_id INTEGER PRIMARY KEY,
                source TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        con.execute("""
            CREATE INDEX IF NOT EXISTS idx_orders_user_created
            ON orders(user_id, created_at)
        """)

        con.execute("""
            CREATE INDEX IF NOT EXISTS idx_bonus_transactions_order_type
            ON bonus_transactions(order_id, user_id, type)
        """)

        con.execute("""
            CREATE INDEX IF NOT EXISTS idx_cart_user
            ON cart(user_id)
        """)

        repair_cashback_amounts(con)

        con.commit()



def ensure_image_storage_columns():
    with connect() as con:
        category_cols = [r["name"] for r in con.execute("PRAGMA table_info(categories)").fetchall()]
        product_cols = [r["name"] for r in con.execute("PRAGMA table_info(products)").fetchall()]

        if "image_path" not in category_cols:
            con.execute("ALTER TABLE categories ADD COLUMN image_path TEXT")

        if "photo_path" not in product_cols:
            con.execute("ALTER TABLE products ADD COLUMN photo_path TEXT")

        con.commit()


def register_user(user_id: int, username: str | None):
    with connect() as con:
        con.execute("""
            INSERT OR IGNORE INTO users (user_id, username)
            VALUES (?, ?)
        """, (user_id, username))
        con.execute("""
            UPDATE users
            SET username = ?
            WHERE user_id = ?
        """, (username, user_id))
        con.commit()

def total_users():
    with connect() as con:
        return con.execute("SELECT COUNT(*) FROM users").fetchone()[0]

def users_today():
    with connect() as con:
        return con.execute("""
            SELECT COUNT(*)
            FROM users
            WHERE DATE(first_seen) = DATE('now')
        """).fetchone()[0]

def users_week():
    with connect() as con:
        return con.execute("""
            SELECT COUNT(*)
            FROM users
            WHERE DATE(first_seen) >= DATE('now', '-7 days')
        """).fetchone()[0]

def users_month():
    with connect() as con:
        return con.execute("""
            SELECT COUNT(*)
            FROM users
            WHERE DATE(first_seen) >= DATE('now', '-30 days')
        """).fetchone()[0]

def add_category(name: str, emoji: str = "", image_id: str | None = None, image_path: str | None = None):
    with connect() as con:
        ensure_image_storage_columns()
        con.execute(
            "INSERT INTO categories (name, emoji, image_id, image_path) VALUES (?, ?, ?, ?)",
            (name, emoji, image_id, image_path)
        )
        con.commit()

def list_categories():
    with connect() as con:
        return con.execute("SELECT * FROM categories ORDER BY id").fetchall()

def get_category(category_id: int):
    with connect() as con:
        return con.execute("SELECT * FROM categories WHERE id = ?", (category_id,)).fetchone()

def delete_category(category_id: int):
    if category_id == 1:
        return False

    with connect() as con:
        con.execute("UPDATE products SET category_id = 1 WHERE category_id = ?", (category_id,))
        con.execute("DELETE FROM categories WHERE id = ?", (category_id,))
        con.commit()
        return True

def update_category_main(
    category_id: int,
    *,
    name: str | None = None,
    emoji: str | None = None,
    image_id: str | None = None,
    image_path: str | None = None,
    clear_image: bool = False
):
    fields = {}

    if name is not None:
        fields["name"] = str(name).strip()

    if emoji is not None:
        fields["emoji"] = str(emoji).strip()

    if clear_image:
        fields["image_id"] = None
        fields["image_path"] = None
    else:
        if image_id is not None:
            fields["image_id"] = image_id
        if image_path is not None:
            fields["image_path"] = image_path

    if not fields:
        return False

    assignments = ", ".join(f"{field} = ?" for field in fields)
    values = list(fields.values()) + [int(category_id)]

    with connect() as con:
        ensure_image_storage_columns()
        con.execute(
            f"UPDATE categories SET {assignments} WHERE id = ?",
            values
        )
        con.commit()

    return True

def add_product(category_id: int, name: str, description: str, variant_options: str | None, price: int, quantity: int, photo_id: str | None, photo_path: str | None = None):
    with connect() as con:
        ensure_image_storage_columns()
        con.execute(
            "INSERT INTO products (category_id, name, description, variant_options, price, quantity, photo_id, photo_path) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (category_id, name, description, variant_options, price, quantity, photo_id, photo_path)
        )
        con.commit()


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
    """
    True только для нового JSON-формата вариантов:
    [{"name": "...", "stock": 10}]

    Старый формат вида "Яблоко\nМанго" не считается отдельным складом вкусов,
    чтобы при подтверждении заказа не раздувать общий остаток.
    """
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


def normalize_variant_stock_input(raw: str | None):
    raw = (raw or "").strip()

    if raw in {"-", "нет", "Нет", "НЕТ", "без вкусов", "Без вкусов", "БЕЗ ВКУСОВ", "no", "none"}:
        return None

    if not raw:
        return None

    variants = []
    seen = set()

    normalized = raw.replace(";", "\n").replace(",", "\n")

    for line in normalized.splitlines():
        line = line.strip()

        if not line or line == "-":
            continue

        name = line
        stock = 0

        match = re.match(r"^(.+?)(?:\s*[:=]\s*|\s+-\s+|\s+)(\d+)$", line)

        if match:
            name = match.group(1).strip()
            stock = int(match.group(2))
        else:
            name = line.strip()
            stock = 0

        if not name:
            continue

        key = name.lower()

        if key in seen:
            continue

        variants.append({"name": name, "stock": max(stock, 0)})
        seen.add(key)

    if not variants:
        return None

    return json.dumps(variants, ensure_ascii=False)


def variant_stock_sum(raw: str | None):
    return sum(int(v["stock"] or 0) for v in parse_variant_stock_options(raw))


def format_variant_stock_options(raw: str | None):
    variants = parse_variant_stock_options(raw)

    if not variants:
        return "без вариантов"

    return "\n".join(f"{v['name']} — {int(v['stock'] or 0)} шт." for v in variants)


def public_variant_names(raw: str | None):
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


def set_variant_stock_options(con, product_id: int, variant_options: str | None):
    if not variant_options:
        con.execute(
            "UPDATE products SET variant_options = ? WHERE id = ?",
            (variant_options, product_id)
        )
        return

    total = variant_stock_sum(variant_options)

    con.execute(
        "UPDATE products SET variant_options = ?, quantity = ? WHERE id = ?",
        (variant_options, total, product_id)
    )


def list_products(category_id: int | None = None):
    with connect() as con:
        if category_id is None:
            return con.execute("SELECT * FROM products WHERE quantity > 0 ORDER BY id DESC").fetchall()

        return con.execute(
            "SELECT * FROM products WHERE category_id = ? AND quantity > 0 ORDER BY id DESC",
            (category_id,)
        ).fetchall()

def list_all_products():
    with connect() as con:
        return con.execute("SELECT * FROM products ORDER BY id DESC").fetchall()

def get_product(product_id: int):
    with connect() as con:
        return con.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()

def delete_product(product_id: int):
    with connect() as con:
        con.execute("DELETE FROM products WHERE id = ?", (product_id,))
        con.execute("DELETE FROM cart WHERE product_id = ?", (product_id,))
        con.commit()

def update_product_field(product_id: int, field: str, value):
    allowed = {
        "category_id",
        "name",
        "description",
        "price",
        "quantity",
        "photo_id",
        "photo_path",
    }

    if field not in allowed:
        raise ValueError("Недопустимое поле товара")

    with connect() as con:
        con.execute(
            f"UPDATE products SET {field} = ? WHERE id = ?",
            (value, int(product_id))
        )
        con.commit()


def update_product_main(
    product_id: int,
    *,
    category_id: int | None = None,
    name: str | None = None,
    description: str | None = None,
    price: int | None = None,
    quantity: int | None = None,
    photo_id: str | None = None,
    photo_path: str | None = None,
    clear_photo: bool = False
):
    fields = {}
    if category_id is not None:
        fields["category_id"] = int(category_id)
    if name is not None:
        fields["name"] = str(name).strip()
    if description is not None:
        fields["description"] = str(description).strip()
    if price is not None:
        fields["price"] = int(price)
    if quantity is not None:
        fields["quantity"] = int(quantity)
    if clear_photo:
        fields["photo_id"] = None
        fields["photo_path"] = None
    else:
        if photo_id is not None:
            fields["photo_id"] = photo_id
        if photo_path is not None:
            fields["photo_path"] = photo_path

    if not fields:
        return False

    assignments = ", ".join(f"{field} = ?" for field in fields)
    values = list(fields.values()) + [int(product_id)]

    with connect() as con:
        con.execute(
            f"UPDATE products SET {assignments} WHERE id = ?",
            values
        )
        con.commit()

    return True


def update_product_variants(product_id: int, variant_options: str | None):
    with connect() as con:
        set_variant_stock_options(con, product_id, variant_options)
        con.commit()


def add_to_cart(user_id: int, product_id: int, variant: str = ""):
    product = get_product(product_id)

    if not product or int(product["quantity"] or 0) <= 0:
        return False

    variant = (variant or "").strip()
    variants = parse_variant_stock_options(product["variant_options"], fallback_stock=product["quantity"])

    if variants:
        available_names = [
            v["name"]
            for v in parse_variant_stock_options(product["variant_options"], fallback_stock=product["quantity"])
            if int(v["stock"] or 0) > 0
        ]

        if not variant or variant not in available_names:
            return False

        available_stock = variant_stock_for(product["variant_options"], variant, fallback_stock=product["quantity"])
    else:
        variant = ""
        available_stock = int(product["quantity"] or 0)

    with connect() as con:
        row = con.execute(
            "SELECT quantity FROM cart WHERE user_id = ? AND product_id = ? AND variant = ?",
            (user_id, product_id, variant)
        ).fetchone()

        current_qty = row["quantity"] if row else 0

        if current_qty + 1 > available_stock:
            return False

        con.execute("""
            INSERT INTO cart (user_id, product_id, variant, quantity)
            VALUES (?, ?, ?, 1)
            ON CONFLICT(user_id, product_id, variant)
            DO UPDATE SET quantity = quantity + 1
        """, (user_id, product_id, variant))
        con.commit()
        return True

def get_cart(user_id: int):
    with connect() as con:
        return con.execute("""
            SELECT c.product_id, c.variant, c.quantity, p.name, p.price, p.quantity AS stock, p.photo_id, p.photo_path, p.description
            FROM cart c
            JOIN products p ON p.id = c.product_id
            WHERE c.user_id = ?
        """, (user_id,)).fetchall()

def clear_cart(user_id: int):
    with connect() as con:
        con.execute("DELETE FROM cart WHERE user_id = ?", (user_id,))
        con.commit()

def normalize_referral_code_db(value: str | None) -> str | None:
    if not value:
        return None

    code = str(value).strip()

    if code.startswith("/start "):
        code = code.split(maxsplit=1)[1]

    if code.startswith("ref_"):
        code = code[4:]

    code = code.upper().replace(" ", "")
    code = re.sub(r"[^A-Z0-9]", "", code)

    if not code.startswith("SYN"):
        return None

    if len(code) < 6 or len(code) > 32:
        return None

    return code


def find_referrer_id_by_code(con, ref_code: str | None) -> int:
    code = normalize_referral_code_db(ref_code)
    if not code:
        return 0

    row = con.execute(
        "SELECT user_id FROM bonus_accounts WHERE referral_code = ?",
        (code,)
    ).fetchone()

    if row and int(row["user_id"] or 0) > 0:
        return int(row["user_id"])

    # Совместимость со старым форматом SYN<telegram_id>.
    # Это не новая антифрод-система, просто чтобы старые ссылки не ломались.
    raw = code[3:]
    if raw.isdigit():
        return int(raw)

    return 0


def bind_referrer_from_code(user_id: int, username: str | None, ref_code: str | None):
    user_id = int(user_id)
    code = normalize_referral_code_db(ref_code)

    if not code:
        return {"ok": False, "reason": "empty_code"}

    with connect() as con:
        register_user(user_id, username)

        invited_account = get_or_create_bonus_account(con, user_id)
        if invited_account and invited_account["referrer_id"]:
            return {
                "ok": True,
                "reason": "already_bound",
                "user_id": user_id,
                "referrer_id": int(invited_account["referrer_id"]),
                "referral_code": code,
            }

        referrer_id = find_referrer_id_by_code(con, code)

        if not referrer_id:
            return {"ok": False, "reason": "referrer_not_found", "referral_code": code}

        if referrer_id == user_id:
            return {"ok": False, "reason": "self_referral", "referral_code": code}

        # Создаём аккаунт пригласившего, если это старая ссылка SYN<telegram_id>.
        get_or_create_bonus_account(con, referrer_id)

        con.execute(
            """
            UPDATE bonus_accounts
            SET referrer_id = ?
            WHERE user_id = ? AND referrer_id IS NULL
            """,
            (referrer_id, user_id)
        )

        if "ensure_referral_link" in globals():
            ensure_referral_link(con, user_id, referrer_id, code)

        con.commit()

        return {
            "ok": True,
            "reason": "bound",
            "user_id": user_id,
            "referrer_id": referrer_id,
            "referral_code": code,
        }


def make_referral_code(user_id: int) -> str:
    return f"SYN{int(user_id)}"


def get_or_create_bonus_account(con, user_id: int):
    user_id = int(user_id)
    code = make_referral_code(user_id)

    row = con.execute("SELECT * FROM bonus_accounts WHERE user_id = ?", (user_id,)).fetchone()

    if not row:
        con.execute(
            "INSERT OR IGNORE INTO bonus_accounts (user_id, balance, referral_code) VALUES (?, 0, ?)",
            (user_id, code)
        )
        row = con.execute("SELECT * FROM bonus_accounts WHERE user_id = ?", (user_id,)).fetchone()

    return row


def add_bonus_transaction(con, user_id: int, amount: int, tx_type: str, order_id: int | None = None, note: str | None = None):
    amount = int(amount or 0)
    if amount == 0:
        return

    get_or_create_bonus_account(con, int(user_id))

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


def referral_link_paid(con, invited_user_id: int) -> bool:
    row = con.execute(
        "SELECT paid FROM referral_links WHERE invited_user_id = ?",
        (int(invited_user_id),)
    ).fetchone()

    return bool(row and int(row["paid"] or 0))


def mark_referral_link_paid(con, invited_user_id: int, order_id: int, reward: int):
    con.execute(
        """
        UPDATE referral_links
        SET first_order_id = COALESCE(first_order_id, ?),
            reward = ?,
            paid = 1,
            paid_at = CURRENT_TIMESTAMP
        WHERE invited_user_id = ?
        """,
        (int(order_id), int(reward), int(invited_user_id))
    )


def order_referrer_id(order, account) -> int:
    # Основной источник — bonus_accounts.referrer_id.
    # Запасной источник — orders.referrer_id, который фиксируется в момент оформления заказа.
    for source in (account, order):
        if not source:
            continue
        try:
            value = int(source["referrer_id"] or 0)
            if value > 0:
                return value
        except Exception:
            pass
    return 0


def referral_already_paid_for_order(con, order_id: int) -> bool:
    row = con.execute(
        "SELECT id FROM bonus_transactions WHERE order_id = ? AND type = 'referral' LIMIT 1",
        (int(order_id),)
    ).fetchone()
    return bool(row)


def order_items_subtotal(con, order_id: int) -> int:
    return int(con.execute(
        """
        SELECT COALESCE(SUM(price * quantity), 0)
        FROM order_items
        WHERE order_id = ?
        """,
        (int(order_id),)
    ).fetchone()[0] or 0)


def repair_cashback_amounts(con):
    rows = con.execute(
        """
        SELECT
            bt.id AS transaction_id,
            bt.user_id,
            bt.order_id,
            bt.amount
        FROM bonus_transactions bt
        JOIN orders o ON o.id = bt.order_id
        WHERE bt.type = 'cashback'
        """
    ).fetchall()

    for row in rows:
        expected = order_items_subtotal(con, row["order_id"]) * 2 // 100
        current = int(row["amount"] or 0)

        if expected == current:
            continue

        difference = expected - current

        con.execute(
            "UPDATE bonus_transactions SET amount = ?, note = ? WHERE id = ?",
            (
                expected,
                "Кэшбэк 2% от стоимости товаров без доставки и доплаты за дату",
                int(row["transaction_id"])
            )
        )
        con.execute(
            "UPDATE bonus_accounts SET balance = MAX(balance + ?, 0) WHERE user_id = ?",
            (difference, int(row["user_id"]))
        )
        con.execute(
            "UPDATE orders SET bonus_earned = ? WHERE id = ?",
            (expected, int(row["order_id"]))
        )


def apply_order_bonus_on_confirm(con, order):
    order_id = int(order["id"])
    invited_user_id = int(order["user_id"])

    existing_cashback = con.execute(
        "SELECT id FROM bonus_transactions WHERE order_id = ? AND user_id = ? AND type = 'cashback'",
        (order_id, invited_user_id)
    ).fetchone()

    if existing_cashback:
        bonus_earned = int(order["bonus_earned"] or 0)
    else:
        subtotal = order_items_subtotal(con, order_id)
        bonus_earned = subtotal * 2 // 100

        if bonus_earned > 0:
            add_bonus_transaction(
                con,
                invited_user_id,
                bonus_earned,
                "cashback",
                order_id,
                "Кэшбэк 2% от стоимости товаров без доставки и доплаты за дату"
            )
            con.execute(
                "UPDATE orders SET bonus_earned = ? WHERE id = ?",
                (bonus_earned, order_id)
            )

    account = get_or_create_bonus_account(con, invited_user_id)
    total = int(order["total"] or 0)
    referral_reward = 0
    referrer_id = order_referrer_id(order, account) or referral_link_referrer_id(con, invited_user_id)

    # Реферальный бонус НЕ ограничен одним приглашением на пригласившего.
    # Ограничение только такое: один приглашённый пользователь даёт бонус один раз,
    # за свой первый подтверждённый заказ.
    previous_confirmed = con.execute(
        """
        SELECT COUNT(*) AS cnt
        FROM orders
        WHERE user_id = ?
          AND status = 'confirmed'
          AND id != ?
        """,
        (invited_user_id, order_id)
    ).fetchone()["cnt"]

    already_paid_for_invited = referral_link_paid(con, invited_user_id)
    already_paid_for_order = referral_already_paid_for_order(con, order_id)

    if referrer_id and previous_confirmed == 0 and not already_paid_for_invited and not already_paid_for_order:
        ensure_referral_link(con, invited_user_id, int(referrer_id), None)

        referral_reward = 150 if total >= 2000 else 100

        get_or_create_bonus_account(con, int(referrer_id))
        add_bonus_transaction(
            con,
            int(referrer_id),
            referral_reward,
            "referral",
            order_id,
            f"Бонус за приглашенного друга {invited_user_id}"
        )

        mark_referral_link_paid(con, invited_user_id, order_id, referral_reward)

        con.execute(
            "UPDATE bonus_accounts SET referral_bonus_paid = 1 WHERE user_id = ?",
            (invited_user_id,)
        )

        try:
            con.execute(
                "UPDATE orders SET referral_reward = ?, referrer_id = ? WHERE id = ?",
                (referral_reward, int(referrer_id), order_id)
            )
        except sqlite3.OperationalError:
            pass

    return bonus_earned, referral_reward



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


def create_promocode(code: str, percent: int, usage_limit: int = 0):
    code = normalize_promocode(code)
    percent = int(percent)
    usage_limit = int(usage_limit or 0)

    if not code:
        raise ValueError("Промокод не должен быть пустым")

    if percent < 1 or percent > 100:
        raise ValueError("Процент должен быть от 1 до 100")

    if usage_limit < 0:
        raise ValueError("Количество использований не может быть меньше 0")

    with connect() as con:
        ensure_promocode_tables()
        con.execute(
            """
            INSERT INTO promocodes (code, percent, usage_limit, used_count, active)
            VALUES (?, ?, ?, 0, 1)
            ON CONFLICT(code)
            DO UPDATE SET percent = excluded.percent,
                          usage_limit = excluded.usage_limit,
                          used_count = 0,
                          active = 1
            """,
            (code, percent, usage_limit)
        )
        con.commit()

    return {"code": code, "percent": percent, "usage_limit": usage_limit}


def get_promocode(code: str):
    code = normalize_promocode(code)

    if not code:
        return None

    with connect() as con:
        ensure_promocode_tables()
        cleanup_expired_promocodes(con)
        con.commit()
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


def list_promocodes():
    with connect() as con:
        ensure_promocode_tables()
        cleanup_expired_promocodes(con)
        con.commit()
        return con.execute(
            "SELECT * FROM promocodes ORDER BY created_at DESC, code"
        ).fetchall()


def delete_promocode(code: str):
    code = normalize_promocode(code)

    if not code:
        return False

    with connect() as con:
        ensure_promocode_tables()
        cur = con.execute("DELETE FROM promocodes WHERE code = ?", (code,))
        con.commit()
        return cur.rowcount > 0


def disable_promocode(code: str):
    # Старое имя оставлено для совместимости. Теперь это полное удаление промокода.
    return delete_promocode(code)


def promocode_discount_for_total(code: str | None, amount: int):
    promo = get_promocode(code)

    if not promo:
        return None, 0

    percent = max(1, min(int(promo["percent"] or 0), 100))
    discount = int(amount or 0) * percent // 100

    return promo, discount


def promocode_discount_for_subtotal(code: str | None, subtotal: int):
    # Оставлено для совместимости со старыми вызовами.
    # Теперь скидку нужно считать от суммы товаров + доставка.
    return promocode_discount_for_total(code, subtotal)


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



def create_order(
    user_id: int,
    username: str | None,
    phone: str | None,
    comment: str | None,
    delivery_method: str | None = None,
    delivery_price: int = 0,
    pickup_point: str | None = None,
    mcd_station: str | None = None,
    delivery_address: str | None = None,
    delivery_date: str | None = None,
    date_surcharge: int = 0,
    promo_code: str | None = None
):
    cart = get_cart(user_id)
    if not cart:
        return None

    delivery_price = int(delivery_price or 0)
    subtotal = sum(item["price"] * item["quantity"] for item in cart)
    date_surcharge = int(date_surcharge or 0)
    before_discount_total = subtotal + delivery_price + date_surcharge
    promo, promo_discount = promocode_discount_for_total(promo_code, before_discount_total)
    promo_code_value = promo["code"] if promo else None
    promo_percent = int(promo["percent"] or 0) if promo else 0
    total = max(before_discount_total - promo_discount, 0)

    with connect() as con:
        cur = con.execute(
            """
            INSERT INTO orders (
                user_id, username, phone, total, comment,
                delivery_method, delivery_price, pickup_point, mcd_station, delivery_address, delivery_date, date_surcharge,
                subtotal, promo_code, promo_percent, promo_discount
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id, username, phone, total, comment,
                delivery_method, delivery_price, pickup_point, mcd_station, delivery_address, delivery_date, date_surcharge,
                subtotal, promo_code_value, promo_percent, promo_discount
            )
        )
        order_id = cur.lastrowid

        for item in cart:
            con.execute("""
                INSERT INTO order_items (order_id, product_id, name, variant, price, quantity)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (order_id, item["product_id"], item["name"], item["variant"] if "variant" in item.keys() else None, item["price"], item["quantity"]))

        con.execute("DELETE FROM cart WHERE user_id = ?", (user_id,))
        con.commit()

    return order_id

def get_order(order_id: int):
    with connect() as con:
        return con.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()

def get_order_items(order_id: int):
    with connect() as con:
        return con.execute("SELECT * FROM order_items WHERE order_id = ?", (order_id,)).fetchall()

def get_user_orders(user_id: int):
    with connect() as con:
        return con.execute("""
            SELECT *
            FROM orders
            WHERE user_id = ?
            ORDER BY id DESC
        """, (user_id,)).fetchall()

def list_user_order_dates(user_id: int):
    with connect() as con:
        return con.execute("""
            SELECT DATE(created_at) AS order_date, COUNT(*) AS count
            FROM orders
            WHERE user_id = ?
            GROUP BY DATE(created_at)
            ORDER BY order_date DESC
        """, (user_id,)).fetchall()

def list_user_orders_by_date(user_id: int, order_date: str):
    with connect() as con:
        return con.execute("""
            SELECT *
            FROM orders
            WHERE user_id = ?
              AND DATE(created_at) = ?
            ORDER BY id DESC
        """, (user_id, order_date)).fetchall()

def confirm_order(order_id: int):
    with connect() as con:
        order = con.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
        if not order or order["status"] != "new":
            return False

        items = con.execute("SELECT * FROM order_items WHERE order_id = ?", (order_id,)).fetchall()

        con.execute("BEGIN IMMEDIATE")

        for item in items:
            product = con.execute(
                "SELECT quantity, variant_options FROM products WHERE id = ?",
                (item["product_id"],)
            ).fetchone()

            if not product:
                con.rollback()
                return False

            explicit_variant_stock = variant_options_have_explicit_stock(product["variant_options"])
            variants = parse_variant_stock_options(product["variant_options"], fallback_stock=product["quantity"])

            if variants and explicit_variant_stock:
                available_stock = variant_stock_for(product["variant_options"], item["variant"], fallback_stock=product["quantity"])
            else:
                # Старые варианты без складов используют общий остаток товара.
                available_stock = int(product["quantity"] or 0)

            if available_stock < int(item["quantity"] or 0):
                con.rollback()
                return False

        # Промокод считается использованным только после подтверждения заказа.
        if order["promo_code"]:
            if not increment_promocode_usage(con, order["promo_code"]):
                con.rollback()
                return False

        for item in items:
            product = con.execute(
                "SELECT quantity, variant_options FROM products WHERE id = ?",
                (item["product_id"],)
            ).fetchone()

            explicit_variant_stock = variant_options_have_explicit_stock(product["variant_options"])
            variants = parse_variant_stock_options(product["variant_options"], fallback_stock=product["quantity"])

            if variants and explicit_variant_stock:
                updated = []

                for variant_item in variants:
                    stock = int(variant_item["stock"] or 0)

                    if variant_item["name"] == item["variant"]:
                        stock = max(stock - int(item["quantity"] or 0), 0)

                    updated.append({"name": variant_item["name"], "stock": stock})

                variant_options = json.dumps(updated, ensure_ascii=False)
                con.execute(
                    "UPDATE products SET variant_options = ?, quantity = ? WHERE id = ?",
                    (variant_options, sum(v["stock"] for v in updated), item["product_id"])
                )
            else:
                # Для товара без вариантов или со старыми вариантами списываем общий остаток.
                con.execute(
                    "UPDATE products SET quantity = MAX(quantity - ?, 0) WHERE id = ?",
                    (item["quantity"], item["product_id"])
                )

        bonus_earned, referral_reward = apply_order_bonus_on_confirm(con, order)

        con.execute("UPDATE orders SET status = 'confirmed' WHERE id = ?", (order_id,))
        con.commit()
        return {
            "ok": True,
            "bonus_earned": bonus_earned,
            "referral_reward": referral_reward
        }

def cancel_order(order_id: int):
    import json
    with connect() as con:
        order = con.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
        if not order:
            return False

        if order["status"] == "cancelled":
            return True

        if order["status"] == "confirmed":
            # 1. Возврат товаров на склад
            items = con.execute("SELECT product_id, quantity, variant FROM order_items WHERE order_id = ?", (order_id,)).fetchall()
            for item in items:
                product = con.execute("SELECT quantity, variant_options FROM products WHERE id = ?", (item["product_id"],)).fetchone()
                if not product:
                    continue

                con.execute("UPDATE products SET quantity = quantity + ? WHERE id = ?", (item["quantity"], item["product_id"]))

                if product["variant_options"] and item["variant"]:
                    try:
                        variants = json.loads(product["variant_options"])
                        updated = []
                        for v in variants:
                            if isinstance(v, dict) and str(v.get("name")) == str(item["variant"]):
                                v["stock"] = int(v.get("stock", 0)) + int(item["quantity"])
                            updated.append(v)
                        con.execute("UPDATE products SET variant_options = ? WHERE id = ?", (json.dumps(updated, ensure_ascii=False), item["product_id"]))
                    except Exception:
                        pass
            
            # 2. СПИСАНИЕ БАЛЛОВ
            earned_txs = con.execute("SELECT id, user_id, amount FROM bonus_transactions WHERE order_id = ? AND amount > 0 AND type NOT IN ('refund', 'revoke')", (order_id,)).fetchall()
            for tx in earned_txs:
                already_revoked = con.execute("SELECT id FROM bonus_transactions WHERE order_id = ? AND user_id = ? AND type = 'revoke'", (order_id, tx["user_id"])).fetchone()
                if not already_revoked:
                    try:
                        from db import add_bonus_transaction
                        add_bonus_transaction(con, tx["user_id"], -tx["amount"], "revoke", order_id, "Аннулирование баллов (отмена заказа)")
                    except Exception:
                        con.execute("INSERT INTO bonus_transactions (user_id, amount, type, order_id, description) VALUES (?, ?, 'revoke', ?, 'Аннулирование баллов')", (tx["user_id"], -tx["amount"], order_id))
                        for col in ['balance', 'bonus_balance', 'bonuses', 'bonus']:
                            try: con.execute(f"UPDATE users SET {col} = MAX({col} - ?, 0) WHERE user_id = ?", (tx["amount"], tx["user_id"]))
                            except: pass

        # 3. ВОЗВРАТ ПОТРАЧЕННЫХ БАЛЛОВ
        bonus_used = int(order["bonus_used"] or 0)
        if bonus_used > 0:
            already_refunded = con.execute("SELECT id FROM bonus_transactions WHERE order_id = ? AND user_id = ? AND type = 'refund'", (order_id, int(order["user_id"]))).fetchone()
            if not already_refunded:
                try:
                    from db import add_bonus_transaction
                    add_bonus_transaction(con, int(order["user_id"]), bonus_used, "refund", order_id, "Возврат списанных баллов")
                except Exception:
                    con.execute("INSERT INTO bonus_transactions (user_id, amount, type, order_id, description) VALUES (?, ?, 'refund', ?, 'Возврат списанных баллов')", (int(order["user_id"]), bonus_used, order_id))
                    for col in ['balance', 'bonus_balance', 'bonuses', 'bonus']:
                        try: con.execute(f"UPDATE users SET {col} = {col} + ? WHERE user_id = ?", (bonus_used, int(order["user_id"])))
                        except: pass

        con.execute("UPDATE orders SET status = 'cancelled' WHERE id = ?", (order_id,))
        con.commit()
        return True

def list_order_dates():
    with connect() as con:
        return con.execute("""
            SELECT DATE(created_at) AS order_date, COUNT(*) AS count
            FROM orders
            GROUP BY DATE(created_at)
            ORDER BY order_date DESC
        """).fetchall()

def list_orders_by_date(order_date: str):
    with connect() as con:
        return con.execute("""
            SELECT *
            FROM orders
            WHERE DATE(created_at) = ?
            ORDER BY id DESC
        """, (order_date,)).fetchall()

def get_stats():
    with connect() as con:
        total_orders = con.execute("SELECT COUNT(*) FROM orders").fetchone()[0]

        new_orders = con.execute(
            "SELECT COUNT(*) FROM orders WHERE status = 'new'"
        ).fetchone()[0]

        confirmed_orders = con.execute(
            "SELECT COUNT(*) FROM orders WHERE status = 'confirmed'"
        ).fetchone()[0]

        cancelled_orders = con.execute(
            "SELECT COUNT(*) FROM orders WHERE status = 'cancelled'"
        ).fetchone()[0]

        revenue = con.execute("""
            SELECT COALESCE(SUM(total), 0)
            FROM orders
            WHERE status = 'confirmed'
        """).fetchone()[0]

        today_revenue = con.execute("""
            SELECT COALESCE(SUM(total), 0)
            FROM orders
            WHERE status = 'confirmed'
              AND DATE(created_at) = DATE('now')
        """).fetchone()[0]

        week_revenue = con.execute("""
            SELECT COALESCE(SUM(total), 0)
            FROM orders
            WHERE status = 'confirmed'
              AND DATE(created_at) >= DATE('now', '-7 days')
        """).fetchone()[0]

        month_revenue = con.execute("""
            SELECT COALESCE(SUM(total), 0)
            FROM orders
            WHERE status = 'confirmed'
              AND DATE(created_at) >= DATE('now', '-30 days')
        """).fetchone()[0]

        clients = con.execute(
            "SELECT COUNT(DISTINCT user_id) FROM orders"
        ).fetchone()[0]

        products = con.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        categories = con.execute("SELECT COUNT(*) FROM categories").fetchone()[0]

        avg_check = 0
        if confirmed_orders:
            avg_check = round(revenue / confirmed_orders)

        return {
            "total_orders": total_orders,
            "new_orders": new_orders,
            "confirmed_orders": confirmed_orders,
            "cancelled_orders": cancelled_orders,
            "revenue": revenue,
            "today_revenue": today_revenue,
            "week_revenue": week_revenue,
            "month_revenue": month_revenue,
            "clients": clients,
            "users_total": total_users(),
            "users_today": users_today(),
            "users_week": users_week(),
            "users_month": users_month(),
            "products": products,
            "categories": categories,
            "avg_check": avg_check,
        }

def is_admin(user_id: int) -> bool:
    from config import ADMINS
    return int(user_id) in ADMINS


def list_all_orders():
    with connect() as con:
        return con.execute("""
            SELECT *
            FROM orders
            ORDER BY id DESC
        """).fetchall()


def update_cart_quantity(user_id: int, product_id: int, quantity: int, variant: str = ""):
    with connect() as con:
        if quantity <= 0:
            con.execute("DELETE FROM cart WHERE user_id = ? AND product_id = ? AND variant = ?", (user_id, product_id, variant))
        else:
            con.execute("""
                INSERT INTO cart (user_id, product_id, variant, quantity)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id, product_id, variant)
                DO UPDATE SET quantity = excluded.quantity
            """, (user_id, product_id, variant, quantity))
        con.commit()


def register_user_from_app(user_id: int, username: str | None = None):
    with connect() as con:
        con.execute(
            """
            INSERT INTO users (user_id, username)
            VALUES (?, ?)
            ON CONFLICT(user_id)
            DO UPDATE SET username = excluded.username
            """,
            (int(user_id), username or "")
        )
        con.commit()



def reset_user_test_data(user_id: int):
    """
    Полное удаление пользователя из бота для тестов.
    Дополнительно корректно откатывает влияние удаляемых bonus_transactions
    на балансы других пользователей, например реферальный бонус пригласившего.
    """
    user_id = int(user_id)

    with connect() as con:
        own_orders = con.execute(
            "SELECT id, status, promo_code FROM orders WHERE user_id = ?",
            (user_id,)
        ).fetchall()
        own_order_ids = [int(row["id"]) for row in own_orders]

        order_placeholders = ",".join("?" for _ in own_order_ids)

        # Все транзакции, которые будут удалены:
        # - транзакции самого пользователя
        # - транзакции по заказам пользователя, включая referral-транзакции пригласившего
        tx_params = [user_id]
        tx_sql = "SELECT id, user_id, amount FROM bonus_transactions WHERE user_id = ?"

        if own_order_ids:
            tx_sql += f" OR order_id IN ({order_placeholders})"
            tx_params.extend(own_order_ids)

        tx_rows = con.execute(tx_sql, tx_params).fetchall()

        for tx in tx_rows:
            tx_user_id = int(tx["user_id"])
            amount = int(tx["amount"] or 0)

            # Убираем эффект транзакции из баланса.
            # Если amount был +150, баланс уменьшится на 150.
            # Если amount был -100, баланс увеличится на 100.
            con.execute(
                "UPDATE bonus_accounts SET balance = MAX(balance - ?, 0) WHERE user_id = ?",
                (amount, tx_user_id)
            )

        if tx_rows:
            tx_ids = [int(row["id"]) for row in tx_rows]
            tx_placeholders = ",".join("?" for _ in tx_ids)
            con.execute(f"DELETE FROM bonus_transactions WHERE id IN ({tx_placeholders})", tx_ids)

        # Для старых данных: если промокод уже был списан на подтверждённом заказе,
        # возвращаем использование промокода при полном удалении пользователя.
        for order in own_orders:
            if order["promo_code"] and order["status"] == "confirmed":
                decrement_promocode_usage(con, order["promo_code"])

        for order_id in own_order_ids:
            con.execute("DELETE FROM order_items WHERE order_id = ?", (order_id,))

        con.execute("DELETE FROM orders WHERE user_id = ?", (user_id,))
        con.execute("DELETE FROM cart WHERE user_id = ?", (user_id,))

        con.execute(
            "DELETE FROM referral_links WHERE invited_user_id = ? OR referrer_id = ?",
            (user_id, user_id)
        )

        try:
            con.execute(
                "UPDATE orders SET referrer_id = 0, referral_reward = 0 WHERE referrer_id = ?",
                (user_id,)
            )
        except sqlite3.OperationalError:
            pass

        con.execute(
            """
            UPDATE bonus_accounts
            SET referrer_id = NULL,
                referral_bonus_paid = 0
            WHERE referrer_id = ?
            """,
            (user_id,)
        )

        con.execute("DELETE FROM bonus_accounts WHERE user_id = ?", (user_id,))
        con.execute("DELETE FROM users WHERE user_id = ?", (user_id,))

        try:
            con.execute("DELETE FROM admin_targets WHERE chat_id = ?", (user_id,))
        except sqlite3.OperationalError:
            pass

        con.commit()

        return {
            "user_id": user_id,
            "deleted_orders": len(own_order_ids),
            "deleted_bonus_transactions": len(tx_rows),
            "fully_removed": True,
        }


def reset_referral_between(referrer_id: int, invited_user_id: int):
    referrer_id = int(referrer_id)
    invited_user_id = int(invited_user_id)

    with connect() as con:
        invited_orders = con.execute(
            "SELECT id FROM orders WHERE user_id = ?",
            (invited_user_id,)
        ).fetchall()
        invited_order_ids = [int(row["id"]) for row in invited_orders]

        # Удаляем старые реферальные транзакции именно по этому приглашённому.
        old_ref_txs = con.execute(
            """
            SELECT id, user_id, amount
            FROM bonus_transactions
            WHERE type = 'referral'
              AND (note LIKE ? OR order_id IN (SELECT id FROM orders WHERE user_id = ?))
            """,
            (f"%{invited_user_id}%", invited_user_id)
        ).fetchall()

        for tx in old_ref_txs:
            con.execute(
                "UPDATE bonus_accounts SET balance = MAX(balance - ?, 0) WHERE user_id = ?",
                (int(tx["amount"] or 0), int(tx["user_id"]))
            )
            con.execute("DELETE FROM bonus_transactions WHERE id = ?", (int(tx["id"]),))

        for order_id in invited_order_ids:
            con.execute("UPDATE orders SET referral_reward = 0, referrer_id = ? WHERE id = ?", (referrer_id, order_id))

        con.execute("DELETE FROM referral_links WHERE invited_user_id = ?", (invited_user_id,))
        ensure_referral_link(con, invited_user_id, referrer_id, None)

        con.execute(
            """
            INSERT OR IGNORE INTO bonus_accounts (user_id, balance, referral_code)
            VALUES (?, 0, ?)
            """,
            (invited_user_id, make_referral_code(invited_user_id))
        )

        con.execute(
            """
            UPDATE bonus_accounts
            SET referrer_id = ?, referral_bonus_paid = 0
            WHERE user_id = ?
            """,
            (referrer_id, invited_user_id)
        )

        con.commit()

        return {
            "referrer_id": referrer_id,
            "invited_user_id": invited_user_id,
            "touched_orders": len(invited_order_ids),
        }



def pay_missing_referral_bonus(order_id: int, referrer_id: int):
    order_id = int(order_id)
    referrer_id = int(referrer_id)

    with connect() as con:
        order = con.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()

        if not order:
            return {"ok": False, "reason": "order_not_found"}

        if order["status"] != "confirmed":
            return {"ok": False, "reason": "order_not_confirmed"}

        invited_user_id = int(order["user_id"])

        if invited_user_id == referrer_id:
            return {"ok": False, "reason": "same_user"}

        if referral_link_paid(con, invited_user_id) or referral_already_paid_for_order(con, order_id):
            return {"ok": False, "reason": "already_paid"}

        previous_confirmed = con.execute(
            """
            SELECT COUNT(*) AS cnt
            FROM orders
            WHERE user_id = ?
              AND status = 'confirmed'
              AND id != ?
            """,
            (invited_user_id, order_id)
        ).fetchone()["cnt"]

        if previous_confirmed > 0:
            return {"ok": False, "reason": "not_first_confirmed_order"}

        total = int(order["total"] or 0)
        reward = 150 if total >= 2000 else 100

        get_or_create_bonus_account(con, referrer_id)
        get_or_create_bonus_account(con, invited_user_id)

        ensure_referral_link(con, invited_user_id, referrer_id, None)

        add_bonus_transaction(
            con,
            referrer_id,
            reward,
            "referral",
            order_id,
            f"Бонус за приглашенного друга {invited_user_id}"
        )

        mark_referral_link_paid(con, invited_user_id, order_id, reward)

        con.execute(
            """
            UPDATE bonus_accounts
            SET referrer_id = ?, referral_bonus_paid = 1
            WHERE user_id = ?
            """,
            (referrer_id, invited_user_id)
        )

        try:
            con.execute(
                "UPDATE orders SET referrer_id = ?, referral_reward = ? WHERE id = ?",
                (referrer_id, reward, order_id)
            )
        except sqlite3.OperationalError:
            pass

        con.commit()

        return {
            "ok": True,
            "order_id": order_id,
            "referrer_id": referrer_id,
            "invited_user_id": invited_user_id,
            "reward": reward,
        }

def get_orders_by_delivery_date(date_str: str):
    with connect() as con:
        return con.execute("SELECT * FROM orders WHERE delivery_date = ? AND status != 'cancelled' ORDER BY id DESC", (date_str,)).fetchall()

def update_order_courier(order_id: int, courier_id: int):
    with connect() as con:
        con.execute("UPDATE orders SET courier_id = ? WHERE id = ?", (int(courier_id), int(order_id)))
        con.commit()

def update_order_status(order_id: int, status: str):
    with connect() as con:
        con.execute("UPDATE orders SET status = ? WHERE id = ?", (status, int(order_id)))
        con.commit()


def get_delivery_dates(status='confirmed'):
    with connect() as con:
        return con.execute('''
            SELECT delivery_date, COUNT(*) as count 
            FROM orders 
            WHERE status = ? 
              AND delivery_date IS NOT NULL 
              AND delivery_date != ''
            GROUP BY delivery_date 
            ORDER BY delivery_date ASC
        ''', (status,)).fetchall()

def get_delivery_stats(date_str: str, status='confirmed'):
    with connect() as con:
        rows = con.execute('''
            SELECT delivery_method, COUNT(*) as count, SUM(total) as sum_total
            FROM orders
            WHERE status = ? AND delivery_date = ?
            GROUP BY delivery_method
        ''', (status, date_str)).fetchall()
        
        total_count = sum(r["count"] for r in rows)
        total_sum = sum(r["sum_total"] or 0 for r in rows)
        by_method = {r["delivery_method"]: r["count"] for r in rows}
        
        return {
            "total_count": total_count,
            "total_sum": total_sum,
            "methods": by_method
        }

def get_deliveries_by_date(date_str: str, method: str = "all", status='confirmed'):
    with connect() as con:
        query = "SELECT * FROM orders WHERE status = ? AND delivery_date = ?"
        params = [status, date_str]
        if method != "all":
            query += " AND delivery_method = ?"
            params.append(method)
        query += " ORDER BY id ASC"
        return con.execute(query, params).fetchall()



def search_orders_admin(query: str):
    query = query.strip()
    with connect() as con:
        if query.isdigit():
            if len(query) <= 5:
                return con.execute(
                    "SELECT * FROM orders WHERE id = ? ORDER BY id DESC LIMIT 20",
                    (int(query),)
                ).fetchall()
            else:
                return con.execute(
                    "SELECT * FROM orders WHERE phone LIKE ? ORDER BY id DESC LIMIT 20",
                    (f"%{query}%",)
                ).fetchall()
        else:
            query_clean = query.replace("@", "")
            return con.execute(
                "SELECT * FROM orders WHERE username LIKE ? ORDER BY id DESC LIMIT 20",
                (f"%{query_clean}%",)
            ).fetchall()
