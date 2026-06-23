import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parent / "bot.db"

with sqlite3.connect(DB) as con:
    con.row_factory = sqlite3.Row

    print("\nPRODUCTS:")
    for row in con.execute("SELECT id, name, quantity FROM products ORDER BY id"):
        print(dict(row))

    print("\nORDERS:")
    for row in con.execute("SELECT id, status, total, created_at FROM orders ORDER BY id DESC LIMIT 10"):
        print(dict(row))

    print("\nORDER ITEMS:")
    for row in con.execute("SELECT order_id, product_id, name, quantity FROM order_items ORDER BY order_id DESC LIMIT 20"):
        print(dict(row))
