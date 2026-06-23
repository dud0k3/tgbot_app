import sys
import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parent / "bot.db"

if len(sys.argv) != 2:
    print("Использование: python restore_stock_from_order.py НОМЕР_ЗАКАЗА")
    raise SystemExit(1)

order_id = int(sys.argv[1])

with sqlite3.connect(DB) as con:
    con.row_factory = sqlite3.Row
    items = con.execute("SELECT product_id, quantity FROM order_items WHERE order_id = ?", (order_id,)).fetchall()

    if not items:
        print("Заказ не найден")
        raise SystemExit(1)

    for item in items:
        con.execute("UPDATE products SET quantity = quantity + ? WHERE id = ?", (item["quantity"], item["product_id"]))

    con.commit()
    print(f"Остатки по заказу №{order_id} возвращены")
