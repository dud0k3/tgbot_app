import os
import html
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.filters import CommandStart, Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

from image_storage import cache_all_db_images, image_storage_status, save_telegram_photo
from config import ADMINS, ORDER_GROUP_ID, WEBAPP_URL, is_admin, is_admin_identity
from db import (
    add_category, list_categories, get_category, delete_category, update_category_main,
    add_product, list_products, list_all_products, get_product, delete_product, update_product_variants, update_product_main,
    parse_variant_stock_options, variant_options_have_explicit_stock,
    add_to_cart, get_cart, clear_cart, create_order,
    get_order, get_order_items, confirm_order, cancel_order, list_all_orders, list_order_dates, list_orders_by_date, list_user_order_dates, list_user_orders_by_date, connect,
    reset_user_test_data,
    reset_referral_between,
    pay_missing_referral_bonus,
    bind_referrer_from_code,
    create_promocode, list_promocodes, delete_promocode,
    normalize_variant_stock_input, format_variant_stock_options, variant_stock_sum, get_stats
)

router = Router()

SUBSCRIPTION_CHANNEL_USERNAME = "syndicate_vape"
SUBSCRIPTION_CHANNEL_URL = f"https://t.me/{SUBSCRIPTION_CHANNEL_USERNAME}"



def is_admin_user(user) -> bool:
    return is_admin_identity(user.id, getattr(user, "username", None))


@router.message(StateFilter("*"), F.text.regexp(r"(?i).*назад.*|.*главное меню.*|.*меню.*"))
async def universal_back(message: Message, state: FSMContext):
    await state.clear()

    if is_admin_user(message.from_user):
        await message.answer("Главное меню:", reply_markup=main_kb(message.from_user))
        return

    await message.answer(
        fake_subscription_text(),
        reply_markup=fake_subscription_kb()
    )


@router.message(StateFilter("*"), Command("cancel"))
async def cancel_current_action(message: Message, state: FSMContext):
    await state.clear()

    if is_admin_user(message.from_user):
        await message.answer("Действие отменено. Главное меню:", reply_markup=main_kb(message.from_user))
        return

    await message.answer("Действие отменено.", reply_markup=main_kb(message.from_user))


class AddCategory(StatesGroup):
    name = State()
    emoji = State()
    image = State()


class EditCategory(StatesGroup):
    category = State()
    name = State()
    emoji = State()
    image = State()

class AddProduct(StatesGroup):
    category = State()
    name = State()
    description = State()
    variants = State()
    price = State()
    quantity = State()
    photo = State()

class EditProductVariants(StatesGroup):
    product = State()
    variants = State()


class EditProductMain(StatesGroup):
    product = State()
    name = State()
    description = State()
    price = State()
    quantity = State()
    photo = State()
    variants = State()


class AddPromocode(StatesGroup):
    code = State()
    percent = State()
    usage_limit = State()


class DeletePromocode(StatesGroup):
    code = State()


class OrderComment(StatesGroup):
    phone = State()
    comment = State()

def parse_callback_id(data: str):
    try:
        return int(str(data).split(":", 1)[1])
    except Exception:
        return None


def remember_admin_target(user):
    if not is_admin_user(user):
        return

    try:
        with connect() as con:
            con.execute(
                "CREATE TABLE IF NOT EXISTS admin_targets (chat_id INTEGER PRIMARY KEY, source TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
            )
            con.execute(
                "INSERT OR IGNORE INTO admin_targets (chat_id, source) VALUES (?, ?)",
                (int(user.id), "admin_private")
            )
            con.commit()
    except Exception:
        pass


def category_title(category):
    emoji = category["emoji"] or ""
    if emoji:
        return f"{emoji} {category['name']}"
    return category["name"]

def main_kb(user):
    if hasattr(user, "id"):
        is_admin_now = is_admin_user(user)
    else:
        is_admin_now = is_admin(int(user))

    if not is_admin_now:
        return ReplyKeyboardRemove(remove_keyboard=True)

    kb = ReplyKeyboardBuilder()
    kb.button(text="🛍 Товары")
    kb.button(text="🛒 Корзина")
    kb.button(text="📦 Мои заказы")
    kb.button(text="💬 Поддержка")
    kb.button(text="⚙️ Админка")

    return kb.adjust(1, 2, 2, 1).as_markup(resize_keyboard=True)


def admin_kb():
    kb = ReplyKeyboardBuilder()
    kb.button(text="➕ Добавить категорию")
    kb.button(text="✏️ Редактировать категорию")
    kb.button(text="🗑 Удалить категорию")
    kb.button(text="➕ Добавить товар")
    kb.button(text="✏️ Редактировать товар")
    kb.button(text="✏️ Редактировать варианты")
    kb.button(text="📦 Все заказы")
    kb.button(text="📊 Статистика")
    kb.button(text="🏬 Склад")
    kb.button(text="🎟 Промокод")
    kb.button(text="🗑 Удалить товар")
    kb.button(text="⬅️ Назад")
    return kb.adjust(2).as_markup(resize_keyboard=True)

def categories_kb(prefix: str = "category"):
    kb = InlineKeyboardBuilder()
    for c in list_categories():
        kb.button(text=category_title(c), callback_data=f"{prefix}:{c['id']}")
    kb.adjust(1)
    return kb.as_markup()

def delete_categories_kb():
    kb = InlineKeyboardBuilder()
    for c in list_categories():
        if c["id"] != 1:
            kb.button(text=f"🗑 {category_title(c)}", callback_data=f"delete_category:{c['id']}")
    kb.adjust(1)
    return kb.as_markup()


def edit_categories_kb():
    kb = InlineKeyboardBuilder()
    for c in list_categories():
        kb.button(text=f"✏️ {category_title(c)}", callback_data=f"edit_category:{c['id']}")
    kb.adjust(1)
    return kb.as_markup()


def edit_category_fields_kb(category_id: int):
    kb = InlineKeyboardBuilder()
    kb.button(text="Название", callback_data=f"edit_category_field:{category_id}:name")
    kb.button(text="Эмодзи", callback_data=f"edit_category_field:{category_id}:emoji")
    kb.button(text="Картинка", callback_data=f"edit_category_field:{category_id}:image")
    kb.button(text="⬅️ К списку категорий", callback_data="edit_category_back")
    kb.adjust(2, 1, 1)
    return kb.as_markup()


def edit_category_summary(category):
    image_status = "есть" if category["image_id"] or category["image_path"] else "нет"
    emoji = category["emoji"] or "нет"

    return (
        f"<b>Редактирование категории</b>\n\n"
        f"<b>ID:</b> <code>{category['id']}</code>\n"
        f"<b>Название:</b> {h(category['name'])}\n"
        f"<b>Эмодзи:</b> {h(emoji)}\n"
        f"<b>Картинка:</b> {image_status}\n\n"
        f"Выберите, что изменить:"
    )

def products_kb(category_id: int):
    kb = InlineKeyboardBuilder()
    for p in list_products(category_id):
        kb.button(text=f"{p['name']} — {p['price']} ₽", callback_data=f"product:{p['id']}")
    kb.button(text="⬅️ К категориям", callback_data="back_categories")
    kb.adjust(1)
    return kb.as_markup()

def product_kb(product_id: int, category_id: int):
    kb = InlineKeyboardBuilder()
    kb.button(text="🛒 Добавить в корзину", callback_data=f"cart_add:{product_id}")
    kb.button(text="⬅️ Назад к товарам", callback_data=f"back_products:{category_id}")
    kb.adjust(1)
    return kb.as_markup()

def cart_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Оформить заказ", callback_data="order_start")
    kb.button(text="🧹 Очистить корзину", callback_data="cart_clear")
    kb.adjust(1)
    return kb.as_markup()

def order_admin_kb(order_id: int):
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Подтвердить", callback_data=f"order_confirm:{order_id}")
    kb.button(text="❌ Отменить", callback_data=f"order_cancel:{order_id}")
    kb.adjust(2)
    return kb.as_markup()


def order_dates_kb():
    kb = InlineKeyboardBuilder()
    for row in list_order_dates():
        date = row["order_date"]
        count = row["count"]
        kb.button(text=f"📅 {date} | заказов: {count}", callback_data=f"orders_date:{date}")
    kb.adjust(1)
    return kb.as_markup()

def user_order_dates_kb(user_id: int):
    kb = InlineKeyboardBuilder()
    for row in list_user_order_dates(user_id):
        date = row["order_date"]
        count = row["count"]
        kb.button(text=f"📅 {date} | заказов: {count}", callback_data=f"user_orders_date:{date}")
    kb.adjust(1)
    return kb.as_markup()

def delete_products_kb():
    kb = InlineKeyboardBuilder()
    for p in list_all_products():
        kb.button(text=f"🗑 {p['name']} | остаток: {p['quantity']}", callback_data=f"delete_product:{p['id']}")
    kb.adjust(1)
    return kb.as_markup()

def edit_variants_products_kb():
    kb = InlineKeyboardBuilder()
    for p in list_all_products():
        variants = format_variant_stock_options(p["variant_options"]).replace("\n", " | ")
        kb.button(text=f"✏️ {p['name']} | {variants}", callback_data=f"edit_variants:{p['id']}")
    kb.adjust(1)
    return kb.as_markup()


def edit_products_kb():
    kb = InlineKeyboardBuilder()
    for p in list_all_products():
        kb.button(
            text=f"✏️ {p['name']} | {p['price']} ₽ | остаток: {p['quantity']}",
            callback_data=f"edit_product:{p['id']}"
        )
    kb.adjust(1)
    return kb.as_markup()


def edit_product_fields_kb(product_id: int):
    kb = InlineKeyboardBuilder()
    kb.button(text="Название", callback_data=f"edit_product_field:{product_id}:name")
    kb.button(text="Описание", callback_data=f"edit_product_field:{product_id}:description")
    kb.button(text="Цена", callback_data=f"edit_product_field:{product_id}:price")
    kb.button(text="Остаток", callback_data=f"edit_product_field:{product_id}:quantity")
    kb.button(text="Категория", callback_data=f"edit_product_field:{product_id}:category")
    kb.button(text="Фото", callback_data=f"edit_product_field:{product_id}:photo")
    kb.button(text="Вкусы / варианты", callback_data=f"edit_product_field:{product_id}:variants")
    kb.button(text="⬅️ К списку товаров", callback_data="edit_product_back")
    kb.adjust(2, 2, 2, 1, 1)
    return kb.as_markup()


def edit_product_categories_kb(product_id: int):
    kb = InlineKeyboardBuilder()
    for c in list_categories():
        kb.button(
            text=category_title(c),
            callback_data=f"edit_product_category:{product_id}:{c['id']}"
        )
    kb.button(text="⬅️ Назад", callback_data=f"edit_product:{product_id}")
    kb.adjust(1)
    return kb.as_markup()


def edit_product_summary(product):
    category = get_category(product["category_id"])
    category_name = category_title(category) if category else "без категории"
    variants = format_variant_stock_options(product["variant_options"])

    photo_status = "есть" if product["photo_id"] or product["photo_path"] else "нет"

    return (
        f"<b>Редактирование товара</b>\n\n"
        f"<b>ID:</b> <code>{product['id']}</code>\n"
        f"<b>Название:</b> {product['name']}\n"
        f"<b>Категория:</b> {category_name}\n"
        f"<b>Цена:</b> {product['price']} ₽\n"
        f"<b>Остаток общий:</b> {product['quantity']} шт.\n"
        f"<b>Фото:</b> {photo_status}\n"
        f"<b>Описание:</b> {product['description'] or '-'}\n\n"
        f"<b>Вкусы / варианты:</b>\n{variants}\n\n"
        f"Выберите, что изменить:"
    )



def h(value) -> str:
    return html.escape(str(value or ""), quote=False)


def is_photo_skip_text(message: Message) -> bool:
    text = (message.text or "").strip().lower()
    return text in {"-", "—", "–", "−", "нет", "no"}


def stock_status_icon(quantity: int) -> str:
    quantity = int(quantity or 0)
    if quantity <= 0:
        return "⛔"
    if quantity <= 3:
        return "⚠️"
    return "✅"


def stock_status_text(quantity: int) -> str:
    quantity = int(quantity or 0)
    if quantity <= 0:
        return "нет в наличии"
    if quantity <= 3:
        return "заканчивается"
    return "в наличии"


def build_stock_report_messages(max_len: int = 3600):
    products = list_all_products()

    category_cache = {}
    category_totals = {}
    total_stock = 0
    in_stock = 0
    out_stock = 0
    low_stock = 0
    with_variants = 0

    product_blocks = []

    for index, product in enumerate(products, start=1):
        quantity = int(product["quantity"] or 0)
        total_stock += quantity

        if quantity > 0:
            in_stock += 1
        else:
            out_stock += 1

        if 0 < quantity <= 3:
            low_stock += 1

        category_id = product["category_id"]
        if category_id not in category_cache:
            category = get_category(category_id)
            category_cache[category_id] = category_title(category) if category else "Без категории"

        category_name = category_cache[category_id]
        if category_name not in category_totals:
            category_totals[category_name] = {"items": 0, "stock": 0}
        category_totals[category_name]["items"] += 1
        category_totals[category_name]["stock"] += quantity

        raw_variants = product["variant_options"]
        variants = parse_variant_stock_options(raw_variants)
        has_explicit_variant_stock = variant_options_have_explicit_stock(raw_variants)

        icon = stock_status_icon(quantity)
        status = stock_status_text(quantity)

        lines = [
            f"{icon} <b>{index}. {h(product['name'])}</b>",
            f"ID: <code>{product['id']}</code>",
            f"Категория: {h(category_name)}",
            f"Цена: {int(product['price'] or 0)} ₽",
            f"Общий остаток: <b>{quantity} шт.</b> — {status}",
        ]

        if variants and has_explicit_variant_stock:
            with_variants += 1
            lines.append("Вкусы / варианты:")
            for variant in variants:
                variant_name = h(variant["name"])
                variant_stock = int(variant["stock"] or 0)
                variant_icon = stock_status_icon(variant_stock)
                lines.append(f"  {variant_icon} {variant_name} — <b>{variant_stock} шт.</b>")
        elif variants:
            with_variants += 1
            names = ", ".join(h(item["name"]) for item in variants)
            lines.append(f"Вкусы / варианты: {names}")
            lines.append("Остатки по вкусам отдельно не заданы — используется общий остаток товара.")
        else:
            lines.append("Вкусы / варианты: нет")

        product_blocks.append("\n".join(lines))

    category_lines = []
    for name, data in sorted(category_totals.items(), key=lambda item: item[0].lower()):
        category_lines.append(f"• {h(name)} — {data['items']} тов., {data['stock']} шт.")

    header = (
        "<b>🏬 Склад</b>\n\n"
        f"Товаров добавлено: <b>{len(products)}</b>\n"
        f"Общий остаток по складу: <b>{total_stock} шт.</b>\n"
        f"В наличии: <b>{in_stock}</b>\n"
        f"Нет в наличии: <b>{out_stock}</b>\n"
        f"Заканчиваются ≤ 3 шт.: <b>{low_stock}</b>\n"
        f"Товаров с вкусами/вариантами: <b>{with_variants}</b>\n"
    )

    if category_lines:
        header += "\n<b>По категориям:</b>\n" + "\n".join(category_lines)
    else:
        header += "\nТовары пока не добавлены."

    messages = [header]

    if not product_blocks:
        return messages

    current = "<b>📋 Остатки по товарам</b>\n\n"
    for block in product_blocks:
        chunk = block + "\n\n"
        if len(current) + len(chunk) > max_len and current.strip() != "<b>📋 Остатки по товарам</b>":
            messages.append(current.rstrip())
            current = "<b>📋 Остатки по товарам</b>\n\n" + chunk
        else:
            current += chunk

    if current.strip():
        messages.append(current.rstrip())

    return messages


def normalize_variants_text(raw: str):
    return normalize_variant_stock_input(raw)


def render_cart(user_id: int):
    cart = get_cart(user_id)
    if not cart:
        return "Корзина пустая."

    lines = ["<b>Ваша корзина:</b>\n"]
    total = 0

    for item in cart:
        subtotal = item["price"] * item["quantity"]
        total += subtotal
        lines.append(f"• {item['name']} x{item['quantity']} — {subtotal} ₽")

    lines.append(f"\n<b>Итого:</b> {total} ₽")
    return "\n".join(lines)


def delivery_label(value):
    return {
        "pickup": "Самовывоз",
        "mcd": "МЦД-3",
        "moscow": "По Москве",
    }.get(value or "", value or "не указан")

def render_order(order_id: int):
    order = get_order(order_id)
    items = get_order_items(order_id)
    username = f"@{order['username']}" if order["username"] else "без username"

    lines = [
        f"<b>Заказ №{order['id']}</b>",
        f"Клиент: {username}",
        f"Telegram ID: <code>{order['user_id']}</code>",
        f"Телефон: {order['phone'] or 'не указан'}",
        f"Статус: {order['status']}",
        f"Дата: {order['created_at']}",
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
        lines.append(f"Дата получения: {order['delivery_date'][8:10]}.{order['delivery_date'][5:7]}.{order['delivery_date'][:4]}")
    if int(order["date_surcharge"] or 0) > 0:
        lines.append(f"День-в-день: +{int(order['date_surcharge'])} ₽")

    lines.extend([
        "",
        "<b>Товары:</b>"
    ])

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

    return "\n".join(lines)

def referral_payload_from_start_message(message: Message) -> str | None:
    text = (message.text or "").strip()
    parts = text.split(maxsplit=1)

    if len(parts) < 2:
        return None

    payload = parts[1].strip()
    if payload.startswith("ref_") or payload.upper().startswith("SYN"):
        return payload

    return None


def webapp_open_kb():
    if not WEBAPP_URL:
        return None

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Открыть магазин",
                    web_app=WebAppInfo(url=WEBAPP_URL)
                )
            ]
        ]
    )


def fake_subscription_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📣 SYNDICATE",
                    url=SUBSCRIPTION_CHANNEL_URL
                )
            ],
            [
                InlineKeyboardButton(
                    text="✅ Проверить подписку",
                    callback_data="fake_sub_check"
                )
            ]
        ]
    )


def fake_subscription_text():
    return (
        "📣 Чтобы пользоваться ботом, подпишитесь на канал ниже "
        "и нажмите «Проверить подписку»."
    )


@router.message(CommandStart())
async def start(message: Message):
    remember_admin_target(message.from_user)

    payload = referral_payload_from_start_message(message)
    bind_result = None

    if payload:
        bind_result = bind_referrer_from_code(
            message.from_user.id,
            message.from_user.username,
            payload
        )

    if bind_result and bind_result.get("ok") and bind_result.get("reason") in {"bound", "already_bound"}:
        text = "Реферальная ссылка активирована. Открой магазин через кнопку ниже."
    elif payload:
        text = "Магазин открыт. Если реферальная ссылка не привязалась, напишите поддержке."
    else:
        text = "Привет! Это магазин. Выберите действие:"

    if is_admin_user(message.from_user):
        await message.answer(text, reply_markup=main_kb(message.from_user))
        if WEBAPP_URL:
            await message.answer("Mini App:", reply_markup=webapp_open_kb())
        return

    await message.answer(
        fake_subscription_text(),
        reply_markup=fake_subscription_kb()
    )


@router.callback_query(F.data == "fake_sub_check")
async def fake_subscription_check(callback: CallbackQuery):
    if is_admin_user(callback.from_user):
        await callback.message.answer("Главное меню:", reply_markup=main_kb(callback.from_user))
        await callback.answer("Готово")
        return

    await callback.answer("Подписка проверена")
    await callback.message.answer(
        "✅ Подписка проверена. Магазин доступен.\n\n"
        "Открой магазин через кнопку APP слева от поля ввода или через кнопку ниже.",
        reply_markup=main_kb(callback.from_user)
    )

    if WEBAPP_URL:
        await callback.message.answer("Открыть магазин:", reply_markup=webapp_open_kb())


@router.message(Command("menu", "admin", "id"))
async def service_commands(message: Message, state: FSMContext):
    remember_admin_target(message.from_user)
    command = (message.text or "").split()[0].lower()

    if command in {"/menu", "/admin"}:
        await state.clear()

    if command == "/id":
        await message.answer(
            f"Ваш Telegram ID: <code>{message.from_user.id}</code>\n"
            f"Username: @{message.from_user.username or 'нет'}\n"
            f"Админ: {'да' if is_admin_user(message.from_user) else 'нет'}",
            reply_markup=main_kb(message.from_user)
        )
        return

    if is_admin_user(message.from_user):
        await message.answer("Главное меню:", reply_markup=main_kb(message.from_user))
        return

    await message.answer(
        fake_subscription_text(),
        reply_markup=fake_subscription_kb()
    )








@router.message(Command("ref_pay"))
async def ref_pay_command(message: Message):
    if not is_admin_user(message.from_user):
        await message.answer("Нет доступа.")
        return

    parts = (message.text or "").split()

    if len(parts) < 3 or not parts[1].isdigit() or not parts[2].isdigit():
        await message.answer(
            "Использование: /ref_pay ORDER_ID REFERRER_ID\n"
            "Начисляет пропущенный реферальный бонус за уже подтверждённый первый заказ."
        )
        return

    result = pay_missing_referral_bonus(int(parts[1]), int(parts[2]))

    if not result.get("ok"):
        await message.answer(f"Не начислено: {result.get('reason')}")
        return

    await message.answer(
        "Реферальный бонус начислен вручную.\n"
        f"Заказ: <code>{result['order_id']}</code>\n"
        f"Пригласивший: <code>{result['referrer_id']}</code>\n"
        f"Приглашённый: <code>{result['invited_user_id']}</code>\n"
        f"Баллы: +{result['reward']}"
    )




@router.message(Command("ref_bind"))
async def ref_bind_command(message: Message):
    if not is_admin_user(message.from_user):
        await message.answer("Нет доступа.")
        return

    parts = (message.text or "").split()

    if len(parts) < 3 or not parts[1].isdigit():
        await message.answer(
            "Использование: /ref_bind INVITED_USER_ID REF_CODE\n"
            "Например: /ref_bind 1029660017 ref_SYN123456789"
        )
        return

    result = bind_referrer_from_code(int(parts[1]), None, parts[2])

    await message.answer(
        "Результат привязки:\n"
        f"ok={result.get('ok')}\n"
        f"reason={result.get('reason')}\n"
        f"user_id={result.get('user_id')}\n"
        f"referrer_id={result.get('referrer_id')}\n"
        f"code={result.get('referral_code')}"
    )


@router.message(Command("ref_debug"))
async def referral_debug_command(message: Message):
    if not is_admin_user(message.from_user):
        await message.answer("Нет доступа.")
        return

    parts = (message.text or "").split()

    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer(
            "Использование: /ref_debug TELEGRAM_ID\n"
            "Покажет referrer_id, referral_bonus_paid и последние заказы пользователя."
        )
        return

    target_id = int(parts[1])

    from db import connect
    with connect() as con:
        account = con.execute("SELECT * FROM bonus_accounts WHERE user_id = ?", (target_id,)).fetchone()
        orders = con.execute(
            """
            SELECT id, status, total, referrer_id, referral_reward, bonus_earned, created_at
            FROM orders
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT 5
            """,
            (target_id,)
        ).fetchall()

        txs = con.execute(
            """
            SELECT user_id, amount, type, order_id, note, created_at
            FROM bonus_transactions
            WHERE order_id IN (SELECT id FROM orders WHERE user_id = ?)
               OR note LIKE ?
               OR user_id = ?
            ORDER BY id DESC
            LIMIT 10
            """,
            (target_id, f"%{target_id}%", target_id)
        ).fetchall()

        links = con.execute(
            """
            SELECT *
            FROM referral_links
            WHERE invited_user_id = ? OR referrer_id = ?
            ORDER BY created_at DESC
            LIMIT 10
            """,
            (target_id, target_id)
        ).fetchall()

    lines = [f"<b>Referral debug для {target_id}</b>"]

    if account:
        lines.append(
            f"account: balance={account['balance']}, code={account['referral_code']}, "
            f"referrer_id={account['referrer_id']}, paid={account['referral_bonus_paid']}"
        )
    else:
        lines.append("account: нет bonus_accounts")

    lines.append("\n<b>Заказы:</b>")
    if orders:
        for order in orders:
            lines.append(
                f"#{order['id']} {order['status']} total={order['total']} "
                f"referrer={order['referrer_id']} reward={order['referral_reward']} cashback={order['bonus_earned']}"
            )
    else:
        lines.append("нет заказов")

    lines.append("\n<b>Referral links:</b>")
    if links:
        for link in links:
            lines.append(
                f"invited={link['invited_user_id']} referrer={link['referrer_id']} "
                f"paid={link['paid']} reward={link['reward']} first_order={link['first_order_id']}"
            )
    else:
        lines.append("нет referral_links")

    lines.append("\n<b>Транзакции:</b>")
    if txs:
        for tx in txs:
            lines.append(f"{tx['type']} user={tx['user_id']} amount={tx['amount']} order={tx['order_id']} note={tx['note'] or '-'}")
    else:
        lines.append("нет транзакций")

    await message.answer("\n".join(lines[:35]))


@router.message(Command("reset_ref_test"))
async def reset_ref_test_command(message: Message):
    if not is_admin_user(message.from_user):
        await message.answer("Нет доступа.")
        return

    parts = (message.text or "").split()

    if len(parts) < 3 or not parts[1].isdigit() or not parts[2].isdigit():
        await message.answer(
            "Использование: /reset_ref_test REFERRER_ID INVITED_USER_ID\n"
            "Команда заново привяжет приглашённого к пригласившему и сбросит paid-флаг."
        )
        return

    result = reset_referral_between(int(parts[1]), int(parts[2]))

    await message.answer(
        "Реферальная тестовая связка сброшена.\n"
        f"Пригласивший: <code>{result['referrer_id']}</code>\n"
        f"Приглашённый: <code>{result['invited_user_id']}</code>\n"
        f"Затронуто заказов: {result['touched_orders']}"
    )


@router.message(Command("reset_me_test", "reset_user_test", "reset_user_set"))
async def reset_test_orders_command(message: Message):
    if not is_admin_user(message.from_user):
        await message.answer("Нет доступа.")
        return

    parts = (message.text or "").split()
    command = parts[0].lower()

    if command == "/reset_user_test":
        if len(parts) < 2 or not parts[1].isdigit():
            await message.answer(
                "Использование: /reset_user_test TELEGRAM_ID\n"
                "Также работает: /reset_user_set TELEGRAM_ID\n"
                "Например: /reset_user_test 123456789"
            )
            return
        target_id = int(parts[1])
    else:
        target_id = int(message.from_user.id)

    result = reset_user_test_data(target_id)

    await message.answer(
        "Пользователь полностью удалён из бота для теста.\n\n"
        f"Telegram ID: <code>{result['user_id']}</code>\n"
        f"Удалено заказов: {result['deleted_orders']}\n"
        f"Полностью удалён: {'да' if result.get('fully_removed') else 'нет'}\n\n"
        "Теперь этот пользователь для системы как новый: можно заново открывать реферальную ссылку и тестировать."
    )


@router.message(F.text.contains("Поддержка"))
async def support(message: Message):
    await message.answer("Поддержка: @guapsyndicate", reply_markup=main_kb(message.from_user))


@router.message(F.text.contains("Товары"))
async def show_categories(message: Message):
    categories = list_categories()
    if not categories:
        await message.answer("Категорий пока нет.")
        return
    await message.answer("Выберите категорию:", reply_markup=categories_kb())

@router.callback_query(F.data == "back_categories")
async def back_categories(callback: CallbackQuery):
    await callback.message.edit_text("Выберите категорию:", reply_markup=categories_kb())
    await callback.answer()

@router.callback_query(F.data.startswith("category:"))
async def show_products_in_category(callback: CallbackQuery):
    category_id = int(callback.data.split(":")[1])
    category = get_category(category_id)

    if not category:
        await callback.answer("Категория не найдена.", show_alert=True)
        return

    products = list_products(category_id)
    if not products:
        await callback.message.edit_text(
            f"Категория: <b>{category_title(category)}</b>\n\nТоваров пока нет.",
            reply_markup=products_kb(category_id)
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        f"Категория: <b>{category_title(category)}</b>\nВыберите товар:",
        reply_markup=products_kb(category_id)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("back_products:"))
async def back_products(callback: CallbackQuery):
    category_id = int(callback.data.split(":")[1])
    category = get_category(category_id)
    title = category_title(category) if category else "Категория"
    await callback.message.edit_text(
        f"Категория: <b>{title}</b>\nВыберите товар:",
        reply_markup=products_kb(category_id)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("cart_add:"))
async def cart_add(callback: CallbackQuery):
    product_id = int(callback.data.split(":")[1])
    ok = add_to_cart(callback.from_user.id, product_id)
    await callback.answer("Добавлено в корзину." if ok else "Нет в наличии.", show_alert=not ok)

@router.message(F.text.contains("Корзина"))
async def cart_page(message: Message):
    cart = get_cart(message.from_user.id)
    if not cart:
        await message.answer("Корзина пустая.")
        return
    await message.answer(render_cart(message.from_user.id), reply_markup=cart_kb())

@router.callback_query(F.data == "cart_clear")
async def cart_clear(callback: CallbackQuery):
    clear_cart(callback.from_user.id)
    await callback.message.edit_text("Корзина очищена.")
    await callback.answer()

@router.callback_query(F.data == "order_start")
async def order_start(callback: CallbackQuery, state: FSMContext):
    if not get_cart(callback.from_user.id):
        await callback.answer("Корзина пустая.", show_alert=True)
        return
    await callback.message.answer("Введите ваш номер телефона для связи:")
    await state.set_state(OrderComment.phone)
    await callback.answer()

@router.message(OrderComment.phone)
async def order_phone(message: Message, state: FSMContext):
    await state.update_data(phone=message.text.strip())
    await message.answer("Напишите комментарий к заказу: адрес, время, способ связи.\nЕсли комментарий не нужен — напишите '-'")
    await state.set_state(OrderComment.comment)

@router.message(OrderComment.comment)
async def order_comment(message: Message, state: FSMContext, bot: Bot):
    comment = None if message.text.strip() == "-" else message.text.strip()
    data = await state.get_data()
    phone = data.get("phone")

    order_id = create_order(
        user_id=message.from_user.id,
        username=message.from_user.username,
        phone=phone,
        comment=comment
    )

    await state.clear()

    if not order_id:
        await message.answer("Корзина пустая.")
        return

    await message.answer(
        f"Заказ №{order_id} создан.\n\nОжидайте, скоро с вами свяжется менеджер.",
        reply_markup=main_kb(message.from_user)
    )

    text = render_order(order_id)

    for admin_id in ADMINS:
        await bot.send_message(admin_id, text, reply_markup=order_admin_kb(order_id))

    if ORDER_GROUP_ID:
        await bot.send_message(ORDER_GROUP_ID, text, reply_markup=order_admin_kb(order_id))


@router.message(F.text.contains("Мои заказы"))
async def my_orders(message: Message):
    dates = list_user_order_dates(message.from_user.id)
    if not dates:
        await message.answer("У вас пока нет заказов.")
        return

    await message.answer("Выберите день:", reply_markup=user_order_dates_kb(message.from_user.id))

@router.callback_query(F.data.startswith("user_orders_date:"))
async def user_orders_by_date(callback: CallbackQuery):
    order_date = callback.data.split(":", 1)[1]
    orders = list_user_orders_by_date(callback.from_user.id, order_date)

    if not orders:
        await callback.message.answer("Заказов за этот день нет.")
        await callback.answer()
        return

    await callback.message.answer(f"Ваши заказы за {order_date}:")

    for order in orders:
        await callback.message.answer(render_order(order["id"]))

    await callback.answer()

@router.message(F.text == "⚙️ Админка")
async def admin_panel(message: Message):
    remember_admin_target(message.from_user)

    if is_admin_user(message.from_user):
        await message.answer("Админ-панель:", reply_markup=admin_kb())
        return

    await message.answer(
        "Нет доступа к админке.",
        reply_markup=main_kb(message.from_user)
    )





@router.message(Command("images_status"))
async def images_status_command(message: Message):
    if not is_admin_user(message.from_user):
        await message.answer("Нет доступа.")
        return

    status = image_storage_status(connect)

    await message.answer(
        "Статус картинок:\n\n"
        f"Категорий всего: {status['categories_total']}\n"
        f"Категорий с Telegram file_id: {status['categories_with_file_id']}\n"
        f"Категорий с локальным файлом: {status['categories_with_local_file']}\n"
        f"Категорий без локального файла: {status['categories_missing_local']}\n\n"
        f"Товаров всего: {status['products_total']}\n"
        f"Товаров с Telegram file_id: {status['products_with_file_id']}\n"
        f"Товаров с локальным файлом: {status['products_with_local_file']}\n"
        f"Товаров без локального файла: {status['products_missing_local']}\n\n"
        f"Папка: <code>{status['upload_dir']}</code>\n\n"
        "Если без локального файла больше 0 — укажи OLD_BOT_TOKEN старого бота и выполни /cache_images."
    )


@router.message(Command("cache_images"))
async def cache_images_command(message: Message):
    if not is_admin_user(message.from_user):
        await message.answer("Нет доступа.")
        return

    await message.answer(
        "Начинаю перенос картинок в локальное хранилище. "
        "Если картинки были загружены старым ботом, укажи OLD_BOT_TOKEN в Dockhost."
    )

    result = await cache_all_db_images(
        message.bot,
        connect,
        old_bot_token=os.getenv("OLD_BOT_TOKEN", "")
    )

    await message.answer(
        "Кэширование картинок завершено.\n\n"
        f"Категории уже были локально: {result['categories_already_local']}\n"
        f"Категории сохранено сейчас: {result['categories_cached']}\n"
        f"Категории не удалось: {result['categories_failed']}\n\n"
        f"Товары уже были локально: {result['products_already_local']}\n"
        f"Товары сохранено сейчас: {result['products_cached']}\n"
        f"Товары не удалось: {result['products_failed']}\n\n"
        "Если не удалось больше 0 — значит новый бот не может скачать старые Telegram file_id. "
        "Нужно временно указать OLD_BOT_TOKEN старого бота или заново загрузить фото."
    )




def promocodes_list_text():
    promos = list_promocodes()
    if not promos:
        return "Действующих промокодов пока нет."

    lines = ["<b>Действующие промокоды:</b>"]
    for p in promos[:30]:
        limit = int(p["usage_limit"] or 0)
        used = int(p["used_count"] or 0)
        usage = f"{used}/∞" if limit == 0 else f"{used}/{limit}"
        left = "∞" if limit == 0 else max(limit - used, 0)
        lines.append(
            f"• <code>{p['code']}</code> — {int(p['percent'] or 0)}% | "
            f"использований {usage} | осталось {left}"
        )
    return "\n".join(lines)


def promocodes_stats_text():
    promos = list_promocodes()

    active_count = len(promos)
    unlimited_count = sum(1 for p in promos if int(p["usage_limit"] or 0) == 0)
    limited_count = active_count - unlimited_count
    total_used = sum(int(p["used_count"] or 0) for p in promos)
    finite_left = sum(
        max(int(p["usage_limit"] or 0) - int(p["used_count"] or 0), 0)
        for p in promos
        if int(p["usage_limit"] or 0) > 0
    )

    lines = [
        "<b>🎟 Промокоды</b>",
        "",
        f"<b>Действующих:</b> {active_count}",
        f"Без лимита: {unlimited_count}",
        f"С лимитом: {limited_count}",
        f"Использований всего: {total_used}",
        f"Осталось использований по лимитным: {finite_left}",
        "",
        promocodes_list_text(),
        "",
        "Выберите действие:"
    ]

    return "\n".join(lines)


def promocode_menu_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Добавить промокод", callback_data="promo_add")
    kb.button(text="🗑 Удалить промокод", callback_data="promo_delete_menu")
    kb.adjust(1)
    return kb.as_markup()


def promocode_delete_kb():
    kb = InlineKeyboardBuilder()
    promos = list_promocodes()

    for p in promos[:40]:
        code = str(p["code"])
        percent = int(p["percent"] or 0)
        kb.button(text=f"🗑 {code} — {percent}%", callback_data=f"promo_delete:{code}")

    kb.button(text="✍️ Ввести код вручную", callback_data="promo_delete_manual")
    kb.button(text="⬅️ Назад", callback_data="promo_back")
    kb.adjust(1)
    return kb.as_markup()



@router.message(F.text == "🏬 Склад")
@router.message(Command("stock"))
async def admin_stock(message: Message):
    if not is_admin_user(message.from_user):
        return

    messages = build_stock_report_messages()
    for part in messages:
        await message.answer(part)


@router.message(F.text == "📊 Статистика")
@router.message(Command("stats"))
async def admin_stats(message: Message):
    if not is_admin_user(message.from_user):
        return

    stats = get_stats()

    await message.answer(
        "<b>📊 Статистика магазина</b>\n\n"
        f"<b>Пользователей авторизовано в боте:</b> {stats['users_total']}\n"
        f"Новых сегодня: {stats['users_today']}\n"
        f"Новых за 7 дней: {stats['users_week']}\n"
        f"Новых за 30 дней: {stats['users_month']}\n\n"
        f"<b>Заказы:</b>\n"
        f"Всего: {stats['total_orders']}\n"
        f"Новые: {stats['new_orders']}\n"
        f"Подтверждённые: {stats['confirmed_orders']}\n"
        f"Отменённые: {stats['cancelled_orders']}\n\n"
        f"<b>Выручка:</b>\n"
        f"Сегодня: {stats['today_revenue']} ₽\n"
        f"7 дней: {stats['week_revenue']} ₽\n"
        f"30 дней: {stats['month_revenue']} ₽\n"
        f"Всего: {stats['revenue']} ₽\n"
        f"Средний чек: {stats['avg_check']} ₽\n\n"
        f"<b>Каталог:</b>\n"
        f"Категорий: {stats['categories']}\n"
        f"Товаров: {stats['products']}"
    )


@router.message(F.text == "🎟 Промокод")
@router.message(Command("promo"))
async def promocode_admin_start(message: Message, state: FSMContext):
    if not is_admin_user(message.from_user):
        return

    await state.clear()
    await message.answer(
        promocodes_stats_text(),
        reply_markup=promocode_menu_kb()
    )


@router.callback_query(F.data == "promo_back")
async def promocode_back(callback: CallbackQuery, state: FSMContext):
    if not is_admin_user(callback.from_user):
        return

    await state.clear()
    await callback.message.edit_text(
        promocodes_stats_text(),
        reply_markup=promocode_menu_kb()
    )
    await callback.answer()


@router.callback_query(F.data == "promo_add")
async def promocode_add_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin_user(callback.from_user):
        return

    await state.clear()
    await callback.message.edit_text(
        "Введите название нового промокода.\n"
        "Например: <code>SALE10</code>"
    )
    await state.set_state(AddPromocode.code)
    await callback.answer()


@router.callback_query(F.data == "promo_delete_menu")
async def promocode_delete_menu(callback: CallbackQuery, state: FSMContext):
    if not is_admin_user(callback.from_user):
        return

    await state.clear()

    if not list_promocodes():
        await callback.message.edit_text(
            "Действующих промокодов пока нет.",
            reply_markup=promocode_menu_kb()
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        "Выберите промокод для удаления:",
        reply_markup=promocode_delete_kb()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("promo_delete:"))
async def promocode_delete_selected(callback: CallbackQuery, state: FSMContext):
    if not is_admin_user(callback.from_user):
        return

    code = callback.data.split(":", 1)[1]
    ok = delete_promocode(code)

    await state.clear()
    await callback.message.edit_text(
        ("Промокод удалён.\n\n" if ok else "Промокод не найден.\n\n") + promocodes_stats_text(),
        reply_markup=promocode_menu_kb()
    )
    await callback.answer("Удалено" if ok else "Не найден")


@router.callback_query(F.data == "promo_delete_manual")
async def promocode_delete_manual(callback: CallbackQuery, state: FSMContext):
    if not is_admin_user(callback.from_user):
        return

    await state.clear()
    await callback.message.edit_text(
        "Введите код промокода, который нужно удалить.\n"
        "Например: <code>SALE10</code>"
    )
    await state.set_state(DeletePromocode.code)
    await callback.answer()


@router.message(AddPromocode.code)
async def promocode_code(message: Message, state: FSMContext):
    if not is_admin_user(message.from_user):
        return

    text = (message.text or "").strip()

    lowered = text.lower()

    if lowered.startswith(("del ", "delete ", "rm ", "remove ")):
        await message.answer(
            "Для удаления используйте: 🎟 Промокод → 🗑 Удалить промокод"
        )
        return

    code = text.upper().replace(" ", "")

    if not code or len(code) > 32:
        await message.answer("Название промокода должно быть от 1 до 32 символов.")
        return

    await state.update_data(code=code)
    await message.answer("Введите процент скидки числом от 1 до 100:")
    await state.set_state(AddPromocode.percent)


@router.message(DeletePromocode.code)
async def promocode_delete_manual_save(message: Message, state: FSMContext):
    if not is_admin_user(message.from_user):
        return

    code = (message.text or "").strip().upper().replace(" ", "")

    if not code:
        await message.answer("Введите код промокода.")
        return

    ok = delete_promocode(code)
    await state.clear()
    await message.answer(
        ("Промокод удалён.\n\n" if ok else "Промокод не найден.\n\n") + promocodes_stats_text(),
        reply_markup=promocode_menu_kb()
    )


@router.message(AddPromocode.percent)
async def promocode_percent(message: Message, state: FSMContext):
    if not is_admin_user(message.from_user):
        return

    if not (message.text or "").strip().isdigit():
        await message.answer("Процент должен быть числом от 1 до 100.")
        return

    percent = int(message.text.strip())

    if percent < 1 or percent > 100:
        await message.answer("Процент должен быть от 1 до 100.")
        return

    await state.update_data(percent=percent)
    await message.answer(
        "Введите количество использований промокода.\n"
        "Например: <code>10</code> — промокод можно использовать 10 раз.\n"
        "Напишите <code>0</code>, если без ограничения."
    )
    await state.set_state(AddPromocode.usage_limit)


@router.message(AddPromocode.usage_limit)
async def promocode_usage_limit(message: Message, state: FSMContext):
    if not is_admin_user(message.from_user):
        return

    if not (message.text or "").strip().isdigit():
        await message.answer("Количество использований должно быть числом. 0 = без ограничения.")
        return

    usage_limit = int(message.text.strip())

    if usage_limit < 0:
        await message.answer("Количество использований не может быть меньше 0.")
        return

    data = await state.get_data()

    try:
        promo = create_promocode(data["code"], data["percent"], usage_limit)
    except ValueError as e:
        await message.answer(str(e))
        return

    await state.clear()

    usage_text = "без ограничения" if promo["usage_limit"] == 0 else f"{promo['usage_limit']} раз"

    await message.answer(
        f"Промокод создан:\n\n"
        f"<code>{promo['code']}</code> — скидка {promo['percent']}%\n"
        f"Количество использований: {usage_text}\n"
        f"Скидка действует на товары и доставку.\n\n"
        + promocodes_stats_text(),
        reply_markup=promocode_menu_kb()
    )


@router.message(F.text == "➕ Добавить категорию")
async def add_category_start(message: Message, state: FSMContext):
    if not is_admin_user(message.from_user):
        return
    await message.answer("Введите название категории:")
    await state.set_state(AddCategory.name)

@router.message(AddCategory.name)
async def add_category_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if not name:
        await message.answer("Название не должно быть пустым.")
        return

    await state.update_data(name=name)
    await message.answer("Введите смайлик для категории. Например: 🍎, 💨, 🧃.\nЕсли смайлик не нужен — напишите '-'")
    await state.set_state(AddCategory.emoji)

@router.message(AddCategory.emoji)
async def add_category_emoji(message: Message, state: FSMContext):
    emoji = message.text.strip()
    if emoji == "-":
        emoji = ""

    await state.update_data(emoji=emoji)
    await message.answer("Отправьте картинку категории или напишите '-' если картинка не нужна:")
    await state.set_state(AddCategory.image)

@router.message(AddCategory.image, F.photo)
async def add_category_image_photo(message: Message, state: FSMContext):
    data = await state.get_data()

    try:
        image_id = message.photo[-1].file_id
        image_path = await save_telegram_photo(message.bot, image_id, "category")
        add_category(data["name"], data.get("emoji", ""), image_id, image_path)
    except Exception:
        await message.answer("Такая категория уже есть.", reply_markup=admin_kb())
        await state.clear()
        return

    await state.clear()
    await message.answer("Категория добавлена с картинкой.", reply_markup=admin_kb())

@router.message(AddCategory.image)
async def add_category_image_skip(message: Message, state: FSMContext):
    if not is_photo_skip_text(message):
        await message.answer(
            "Это не картинка категории. Отправьте обычное фото или напишите <code>-</code>, если картинка не нужна.\n\n"
            "Чтобы выйти из добавления категории, напишите /cancel или /admin."
        )
        return

    data = await state.get_data()

    try:
        add_category(data["name"], data.get("emoji", ""), None)
    except Exception:
        await message.answer("Такая категория уже есть.", reply_markup=admin_kb())
        await state.clear()
        return

    await state.clear()
    await message.answer("Категория добавлена.", reply_markup=admin_kb())



@router.message(AddCategory.image, F.content_type != "photo")
async def unsupported_category_image_state(message: Message, state: FSMContext):
    if not is_admin_user(message.from_user):
        return

    if is_photo_skip_text(message):
        data = await state.get_data()

        try:
            add_category(data["name"], data.get("emoji", ""), None)
        except Exception:
            await message.answer("Такая категория уже есть.", reply_markup=admin_kb())
            await state.clear()
            return

        await state.clear()
        await message.answer("Категория добавлена.", reply_markup=admin_kb())
        return

    await message.answer(
        "Нужна именно фотография категории, не стикер/файл/гифка. "
        "Отправьте обычное фото или напишите <code>-</code>."
    )


@router.message(AddProduct.photo, F.content_type != "photo")
async def unsupported_product_photo_state(message: Message, state: FSMContext):
    if not is_admin_user(message.from_user):
        return

    if is_photo_skip_text(message):
        data = await state.get_data()

        add_product(
            category_id=data["category_id"],
            name=data["name"],
            description=data["description"],
            variant_options=data.get("variant_options"),
            price=data["price"],
            quantity=variant_stock_sum(data.get("variant_options")) if data.get("variant_options") else data["quantity"],
            photo_id=None,
            photo_path=None
        )

        await state.clear()
        await message.answer("Товар добавлен без фото.", reply_markup=admin_kb())
        return

    await message.answer(
        "Нужно именно фото товара, не стикер/файл/гифка. "
        "Отправьте обычное фото или напишите <code>-</code>."
    )


@router.message(EditProductMain.photo, F.content_type != "photo")
async def unsupported_media_in_photo_state(message: Message, state: FSMContext):
    if not is_admin_user(message.from_user):
        return

    if is_photo_skip_text(message):
        data = await state.get_data()
        product_id = int(data["product_id"])

        update_product_main(product_id, clear_photo=True)
        product = get_product(product_id)

        await state.set_state(EditProductMain.product)
        await message.answer("Фото удалено.\n\n" + edit_product_summary(product), reply_markup=edit_product_fields_kb(product_id))
        return

    await message.answer(
        "Нужно именно фото товара, не стикер/файл/гифка. "
        "Отправьте обычное фото или напишите <code>-</code>."
    )


@router.message(F.text == "✏️ Редактировать категорию")
@router.message(Command("edit_category"))
async def edit_category_start(message: Message, state: FSMContext):
    if not is_admin_user(message.from_user):
        return

    await state.clear()

    categories = list_categories()
    if not categories:
        await message.answer("Категорий пока нет.")
        return

    await message.answer("Выберите категорию для редактирования:", reply_markup=edit_categories_kb())
    await state.set_state(EditCategory.category)


@router.callback_query(F.data == "edit_category_back")
async def edit_category_back(callback: CallbackQuery, state: FSMContext):
    if not is_admin_user(callback.from_user):
        return

    await callback.message.edit_text("Выберите категорию для редактирования:", reply_markup=edit_categories_kb())
    await state.set_state(EditCategory.category)
    await callback.answer()


@router.callback_query(F.data.startswith("edit_category:"))
async def edit_category_selected(callback: CallbackQuery, state: FSMContext):
    if not is_admin_user(callback.from_user):
        return

    category_id = int(callback.data.split(":", 1)[1])
    category = get_category(category_id)

    if not category:
        await callback.answer("Категория не найдена.", show_alert=True)
        return

    await state.update_data(category_id=category_id, category_name=category["name"])
    await callback.message.edit_text(
        edit_category_summary(category),
        reply_markup=edit_category_fields_kb(category_id)
    )
    await state.set_state(EditCategory.category)
    await callback.answer()


@router.callback_query(F.data.startswith("edit_category_field:"))
async def edit_category_field_selected(callback: CallbackQuery, state: FSMContext):
    if not is_admin_user(callback.from_user):
        return

    _, category_id_raw, field = callback.data.split(":", 2)
    category_id = int(category_id_raw)
    category = get_category(category_id)

    if not category:
        await callback.answer("Категория не найдена.", show_alert=True)
        return

    await state.update_data(category_id=category_id, category_name=category["name"], edit_field=field)

    if field == "name":
        await callback.message.edit_text(
            f"Текущее название: <b>{h(category['name'])}</b>\n\nВведите новое название категории:"
        )
        await state.set_state(EditCategory.name)

    elif field == "emoji":
        current = category["emoji"] or "нет"
        await callback.message.edit_text(
            f"Текущий эмодзи: <b>{h(current)}</b>\n\n"
            "Введите новый эмодзи. Если эмодзи нужно убрать — отправьте <code>-</code>."
        )
        await state.set_state(EditCategory.emoji)

    elif field == "image":
        await callback.message.edit_text(
            "Отправьте новую картинку категории.\n\n"
            "Если нужно удалить картинку — отправьте <code>-</code>."
        )
        await state.set_state(EditCategory.image)

    else:
        await callback.answer("Неизвестное поле.", show_alert=True)
        return

    await callback.answer()


@router.message(EditCategory.name)
async def edit_category_name_save(message: Message, state: FSMContext):
    if not is_admin_user(message.from_user):
        return

    name = (message.text or "").strip()
    if len(name) < 2:
        await message.answer("Название должно быть минимум 2 символа.")
        return

    data = await state.get_data()
    category_id = int(data["category_id"])

    try:
        update_category_main(category_id, name=name)
    except Exception:
        await message.answer("Категория с таким названием уже есть. Введите другое название.")
        return

    category = get_category(category_id)
    await state.update_data(category_name=name)
    await state.set_state(EditCategory.category)
    await message.answer(
        "Название категории обновлено.\n\n" + edit_category_summary(category),
        reply_markup=edit_category_fields_kb(category_id)
    )


@router.message(EditCategory.emoji)
async def edit_category_emoji_save(message: Message, state: FSMContext):
    if not is_admin_user(message.from_user):
        return

    emoji = (message.text or "").strip()
    if emoji in {"-", "—", "–", "−", "нет", "Нет", "НЕТ", "no"}:
        emoji = ""

    data = await state.get_data()
    category_id = int(data["category_id"])

    update_category_main(category_id, emoji=emoji)
    category = get_category(category_id)

    await state.set_state(EditCategory.category)
    await message.answer(
        "Эмодзи категории обновлён.\n\n" + edit_category_summary(category),
        reply_markup=edit_category_fields_kb(category_id)
    )


@router.message(EditCategory.image, F.photo)
async def edit_category_image_save(message: Message, state: FSMContext):
    if not is_admin_user(message.from_user):
        return

    data = await state.get_data()
    category_id = int(data["category_id"])

    image_id = message.photo[-1].file_id
    image_path = await save_telegram_photo(message.bot, image_id, "category")

    update_category_main(category_id, image_id=image_id, image_path=image_path)
    category = get_category(category_id)

    await state.set_state(EditCategory.category)
    await message.answer(
        "Картинка категории обновлена.\n\n" + edit_category_summary(category),
        reply_markup=edit_category_fields_kb(category_id)
    )


@router.message(EditCategory.image)
async def edit_category_image_clear(message: Message, state: FSMContext):
    if not is_admin_user(message.from_user):
        return

    if not is_photo_skip_text(message):
        await message.answer(
            "Это не картинка категории. Отправьте обычное фото или напишите <code>-</code>, чтобы удалить картинку.\n\n"
            "Чтобы выйти из редактирования, напишите /cancel или /admin."
        )
        return

    data = await state.get_data()
    category_id = int(data["category_id"])

    update_category_main(category_id, clear_image=True)
    category = get_category(category_id)

    await state.set_state(EditCategory.category)
    await message.answer(
        "Картинка категории удалена.\n\n" + edit_category_summary(category),
        reply_markup=edit_category_fields_kb(category_id)
    )


@router.message(F.text == "🗑 Удалить категорию")
async def delete_category_start(message: Message):
    if not is_admin_user(message.from_user):
        return

    categories = [c for c in list_categories() if c["id"] != 1]
    if not categories:
        await message.answer("Нет категорий для удаления.")
        return

    await message.answer(
        "Выберите категорию для удаления.\nТовары из неё перейдут в «Без категории».",
        reply_markup=delete_categories_kb()
    )

@router.callback_query(F.data.startswith("delete_category:"))
async def delete_category_callback(callback: CallbackQuery):
    if not is_admin_user(callback.from_user):
        return

    category_id = int(callback.data.split(":")[1])
    category = get_category(category_id)

    if not category:
        await callback.answer("Категория не найдена.", show_alert=True)
        return

    ok = delete_category(category_id)
    if not ok:
        await callback.answer("Эту категорию удалить нельзя.", show_alert=True)
        return

    await callback.message.edit_text(f"Категория «{category_title(category)}» удалена. Товары перенесены в «Без категории».")
    await callback.answer()

@router.message(F.text == "➕ Добавить товар")
async def add_product_start(message: Message, state: FSMContext):
    if not is_admin_user(message.from_user):
        return

    if not list_categories():
        await message.answer("Сначала создайте категорию.")
        return

    await message.answer("Выберите категорию для товара:", reply_markup=categories_kb(prefix="add_product_category"))
    await state.set_state(AddProduct.category)

@router.callback_query(AddProduct.category, F.data.startswith("add_product_category:"))
async def add_product_category_selected(callback: CallbackQuery, state: FSMContext):
    category_id = int(callback.data.split(":")[1])
    await state.update_data(category_id=category_id)
    await callback.message.edit_text("Введите название товара:")
    await state.set_state(AddProduct.name)
    await callback.answer()

@router.message(AddProduct.name)
async def add_product_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await message.answer("Введите описание товара:")
    await state.set_state(AddProduct.description)

@router.message(AddProduct.description)
async def add_product_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text.strip())
    await message.answer(
        "Введите варианты товара и остаток по каждому вкусу.\n\n"
        "Если товар БЕЗ вкусов/вариантов — напишите <code>-</code> или <code>нет</code>.\n\n"
        "Если вкусы есть, формат такой:\n"
        "<code>Яблоко:10</code>\n"
        "<code>Груша:5</code>\n"
        "<code>Манго:0</code>"
    )
    await state.set_state(AddProduct.variants)

@router.message(AddProduct.variants)
async def add_product_variants(message: Message, state: FSMContext):
    variants = normalize_variants_text(message.text)
    await state.update_data(variant_options=variants)

    if variants:
        await message.answer(
            "Варианты сохранены:\n"
            f"{format_variant_stock_options(variants)}\n\n"
            "Введите цену числом:"
        )
    else:
        await message.answer("Введите цену числом:")

    await state.set_state(AddProduct.price)

@router.message(AddProduct.price)
async def add_product_price(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Цена должна быть числом.")
        return

    await state.update_data(price=int(message.text))
    await message.answer(
        "Введите общий остаток на складе.\n"
        "Если у товара есть варианты со складом, можно написать 0 — общий остаток посчитается автоматически."
    )
    await state.set_state(AddProduct.quantity)

@router.message(AddProduct.quantity)
async def add_product_quantity(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Количество должно быть числом.")
        return

    await state.update_data(quantity=int(message.text))
    await message.answer("Отправьте фото товара или напишите '-' если фото не нужно:")
    await state.set_state(AddProduct.photo)

@router.message(AddProduct.photo, F.photo)
async def add_product_photo(message: Message, state: FSMContext):
    data = await state.get_data()

    photo_id = message.photo[-1].file_id
    photo_path = await save_telegram_photo(message.bot, photo_id, "product")

    add_product(
        category_id=data["category_id"],
        name=data["name"],
        description=data["description"],
        variant_options=data.get("variant_options"),
        price=data["price"],
        quantity=variant_stock_sum(data.get("variant_options")) if data.get("variant_options") else data["quantity"],
        photo_id=photo_id,
        photo_path=photo_path
    )

    await state.clear()
    await message.answer("Товар добавлен.", reply_markup=admin_kb())

@router.message(AddProduct.photo)
async def add_product_no_photo(message: Message, state: FSMContext):
    if not is_photo_skip_text(message):
        await message.answer(
            "Это не фото товара. Отправьте обычное фото или напишите <code>-</code>, если фото не нужно.\n\n"
            "Чтобы выйти из добавления товара, напишите /cancel или /admin."
        )
        return

    data = await state.get_data()

    add_product(
        category_id=data["category_id"],
        name=data["name"],
        description=data["description"],
        variant_options=data.get("variant_options"),
        price=data["price"],
        quantity=variant_stock_sum(data.get("variant_options")) if data.get("variant_options") else data["quantity"],
        photo_id=None,
        photo_path=None
    )

    await state.clear()
    await message.answer("Товар добавлен без фото.", reply_markup=admin_kb())



@router.message(F.text == "✏️ Редактировать товар")
@router.message(Command("edit_product"))
async def edit_product_start(message: Message, state: FSMContext):
    if not is_admin_user(message.from_user):
        return

    await state.clear()

    products = list_all_products()
    if not products:
        await message.answer("Товаров нет.")
        return

    await message.answer("Выберите товар для редактирования:", reply_markup=edit_products_kb())
    await state.set_state(EditProductMain.product)


@router.callback_query(F.data == "edit_product_back")
async def edit_product_back(callback: CallbackQuery, state: FSMContext):
    if not is_admin_user(callback.from_user):
        return

    await callback.message.edit_text("Выберите товар для редактирования:", reply_markup=edit_products_kb())
    await state.set_state(EditProductMain.product)
    await callback.answer()


@router.callback_query(F.data.startswith("edit_product:"))
async def edit_product_selected(callback: CallbackQuery, state: FSMContext):
    if not is_admin_user(callback.from_user):
        return

    product_id = int(callback.data.split(":")[1])
    product = get_product(product_id)

    if not product:
        await callback.answer("Товар не найден.", show_alert=True)
        return

    await state.update_data(product_id=product_id, product_name=product["name"])
    await callback.message.edit_text(
        edit_product_summary(product),
        reply_markup=edit_product_fields_kb(product_id)
    )
    await state.set_state(EditProductMain.product)
    await callback.answer()


@router.callback_query(F.data.startswith("edit_product_field:"))
async def edit_product_field_selected(callback: CallbackQuery, state: FSMContext):
    if not is_admin_user(callback.from_user):
        return

    _, product_id_raw, field = callback.data.split(":", 2)
    product_id = int(product_id_raw)
    product = get_product(product_id)

    if not product:
        await callback.answer("Товар не найден.", show_alert=True)
        return

    await state.update_data(product_id=product_id, product_name=product["name"], edit_field=field)

    if field == "name":
        await callback.message.edit_text(
            f"Текущее название: <b>{product['name']}</b>\n\nВведите новое название товара:"
        )
        await state.set_state(EditProductMain.name)

    elif field == "description":
        await callback.message.edit_text(
            f"Текущее описание:\n{product['description'] or '-'}\n\n"
            "Введите новое описание. Если описание нужно убрать — отправьте <code>-</code>."
        )
        await state.set_state(EditProductMain.description)

    elif field == "price":
        await callback.message.edit_text(
            f"Текущая цена: <b>{product['price']} ₽</b>\n\nВведите новую цену числом:"
        )
        await state.set_state(EditProductMain.price)

    elif field == "quantity":
        if product["variant_options"]:
            await callback.message.edit_text(
                "У этого товара есть вкусы/варианты, поэтому общий остаток считается из остатков вкусов.\n\n"
                f"Текущие вкусы:\n{format_variant_stock_options(product['variant_options'])}\n\n"
                "Введите новые вкусы и остатки в формате:\n"
                "<code>Яблоко:10</code>\n"
                "<code>Груша:5</code>\n"
                "<code>Манго:0</code>\n\n"
                "Чтобы убрать вкусы — отправьте <code>-</code> или <code>нет</code>."
            )
            await state.set_state(EditProductMain.variants)
        else:
            await callback.message.edit_text(
                f"Текущий остаток: <b>{product['quantity']} шт.</b>\n\nВведите новый остаток числом:"
            )
            await state.set_state(EditProductMain.quantity)

    elif field == "category":
        await callback.message.edit_text(
            f"Выберите новую категорию для товара «{product['name']}»:",
            reply_markup=edit_product_categories_kb(product_id)
        )
        await state.set_state(EditProductMain.product)

    elif field == "photo":
        await callback.message.edit_text(
            "Отправьте новое фото товара.\n\n"
            "Если нужно удалить фото — отправьте <code>-</code>."
        )
        await state.set_state(EditProductMain.photo)

    elif field == "variants":
        await callback.message.edit_text(
            f"Текущие вкусы/варианты:\n{format_variant_stock_options(product['variant_options'])}\n\n"
            "Если товар должен быть БЕЗ вкусов — отправьте <code>-</code> или <code>нет</code>.\n\n"
            "Если вкусы есть, отправьте их в формате:\n"
            "<code>Яблоко:10</code>\n"
            "<code>Груша:5</code>\n"
            "<code>Манго:0</code>\n\n"
            "Вкус с остатком 0 пропадёт у покупателя."
        )
        await state.set_state(EditProductMain.variants)

    else:
        await callback.answer("Неизвестное поле.", show_alert=True)
        return

    await callback.answer()


@router.callback_query(F.data.startswith("edit_product_category:"))
async def edit_product_category_save(callback: CallbackQuery, state: FSMContext):
    if not is_admin_user(callback.from_user):
        return

    _, product_id_raw, category_id_raw = callback.data.split(":")
    product_id = int(product_id_raw)
    category_id = int(category_id_raw)

    product = get_product(product_id)
    category = get_category(category_id)

    if not product or not category:
        await callback.answer("Товар или категория не найдены.", show_alert=True)
        return

    update_product_main(product_id, category_id=category_id)
    product = get_product(product_id)

    await state.update_data(product_id=product_id, product_name=product["name"])
    await callback.message.edit_text(
        f"Категория обновлена: <b>{category_title(category)}</b>\n\n" + edit_product_summary(product),
        reply_markup=edit_product_fields_kb(product_id)
    )
    await state.set_state(EditProductMain.product)
    await callback.answer("Категория обновлена")


@router.message(EditProductMain.name)
async def edit_product_name_save(message: Message, state: FSMContext):
    if not is_admin_user(message.from_user):
        return

    name = (message.text or "").strip()
    if len(name) < 2:
        await message.answer("Название должно быть минимум 2 символа.")
        return

    data = await state.get_data()
    product_id = int(data["product_id"])

    update_product_main(product_id, name=name)
    product = get_product(product_id)

    await state.update_data(product_name=name)
    await state.set_state(EditProductMain.product)
    await message.answer("Название обновлено.\n\n" + edit_product_summary(product), reply_markup=edit_product_fields_kb(product_id))


@router.message(EditProductMain.description)
async def edit_product_description_save(message: Message, state: FSMContext):
    if not is_admin_user(message.from_user):
        return

    description = (message.text or "").strip()
    if description == "-":
        description = ""

    data = await state.get_data()
    product_id = int(data["product_id"])

    update_product_main(product_id, description=description)
    product = get_product(product_id)

    await state.set_state(EditProductMain.product)
    await message.answer("Описание обновлено.\n\n" + edit_product_summary(product), reply_markup=edit_product_fields_kb(product_id))


@router.message(EditProductMain.price)
async def edit_product_price_save(message: Message, state: FSMContext):
    if not is_admin_user(message.from_user):
        return

    if not (message.text or "").strip().isdigit():
        await message.answer("Цена должна быть числом.")
        return

    price = int(message.text.strip())
    if price < 0:
        await message.answer("Цена не может быть меньше 0.")
        return

    data = await state.get_data()
    product_id = int(data["product_id"])

    update_product_main(product_id, price=price)
    product = get_product(product_id)

    await state.set_state(EditProductMain.product)
    await message.answer("Цена обновлена.\n\n" + edit_product_summary(product), reply_markup=edit_product_fields_kb(product_id))


@router.message(EditProductMain.quantity)
async def edit_product_quantity_save(message: Message, state: FSMContext):
    if not is_admin_user(message.from_user):
        return

    if not (message.text or "").strip().isdigit():
        await message.answer("Остаток должен быть числом.")
        return

    quantity = int(message.text.strip())
    data = await state.get_data()
    product_id = int(data["product_id"])

    update_product_main(product_id, quantity=quantity)
    product = get_product(product_id)

    await state.set_state(EditProductMain.product)
    await message.answer("Остаток обновлён.\n\n" + edit_product_summary(product), reply_markup=edit_product_fields_kb(product_id))


@router.message(EditProductMain.photo, F.photo)
async def edit_product_photo_save(message: Message, state: FSMContext):
    if not is_admin_user(message.from_user):
        return

    data = await state.get_data()
    product_id = int(data["product_id"])

    photo_id = message.photo[-1].file_id
    photo_path = await save_telegram_photo(message.bot, photo_id, "product")

    update_product_main(product_id, photo_id=photo_id, photo_path=photo_path)
    product = get_product(product_id)

    await state.set_state(EditProductMain.product)
    await message.answer("Фото обновлено.\n\n" + edit_product_summary(product), reply_markup=edit_product_fields_kb(product_id))


@router.message(EditProductMain.photo)
async def edit_product_photo_clear(message: Message, state: FSMContext):
    if not is_admin_user(message.from_user):
        return

    if not is_photo_skip_text(message):
        await message.answer(
            "Это не фото товара. Отправьте обычное фото или напишите <code>-</code>, чтобы удалить фото.\n\n"
            "Чтобы выйти из редактирования, напишите /cancel или /admin."
        )
        return

    data = await state.get_data()
    product_id = int(data["product_id"])

    update_product_main(product_id, clear_photo=True)
    product = get_product(product_id)

    await state.set_state(EditProductMain.product)
    await message.answer("Фото удалено.\n\n" + edit_product_summary(product), reply_markup=edit_product_fields_kb(product_id))


@router.message(EditProductMain.variants)
async def edit_product_main_variants_save(message: Message, state: FSMContext):
    if not is_admin_user(message.from_user):
        return

    data = await state.get_data()
    product_id = int(data["product_id"])
    variants = normalize_variants_text(message.text)

    update_product_variants(product_id, variants)
    product = get_product(product_id)

    await state.set_state(EditProductMain.product)

    result = format_variant_stock_options(variants) if variants else "варианты удалены"
    await message.answer(
        f"Вкусы/варианты обновлены:\n{result}\n\n" + edit_product_summary(product),
        reply_markup=edit_product_fields_kb(product_id)
    )


@router.message(F.text == "✏️ Редактировать варианты")
async def edit_product_variants_start(message: Message, state: FSMContext):
    if not is_admin_user(message.from_user):
        return

    products = list_all_products()
    if not products:
        await message.answer("Товаров нет.")
        return

    await message.answer("Выберите товар, у которого нужно изменить варианты:", reply_markup=edit_variants_products_kb())
    await state.set_state(EditProductVariants.product)


@router.callback_query(EditProductVariants.product, F.data.startswith("edit_variants:"))
async def edit_product_variants_selected(callback: CallbackQuery, state: FSMContext):
    if not is_admin_user(callback.from_user):
        return

    product_id = int(callback.data.split(":")[1])
    product = get_product(product_id)

    if not product:
        await callback.answer("Товар не найден.", show_alert=True)
        return

    current = format_variant_stock_options(product["variant_options"])
    await state.update_data(product_id=product_id, product_name=product["name"])

    await callback.message.edit_text(
        f"Товар: {product['name']}\n"
        f"Текущие варианты и остатки:\n{current}\n\n"
        "Если товар должен быть БЕЗ вкусов — отправьте <code>-</code> или <code>нет</code>.\n\n"
        "Если вкусы есть, отправьте их в формате:\n"
        "<code>Яблоко:10</code>\n"
        "<code>Груша:5</code>\n"
        "<code>Манго:0</code>\n\n"
        "Вариант с остатком 0 пропадёт у покупателя."
    )
    await state.set_state(EditProductVariants.variants)
    await callback.answer()


@router.message(EditProductVariants.variants)
async def edit_product_variants_save(message: Message, state: FSMContext):
    if not is_admin_user(message.from_user):
        return

    data = await state.get_data()
    product_id = int(data["product_id"])
    product_name = data.get("product_name", "товар")
    variants = normalize_variants_text(message.text)

    update_product_variants(product_id, variants)
    await state.clear()

    result = format_variant_stock_options(variants) if variants else "варианты удалены"
    await message.answer(
        f"Готово. Варианты и остатки товара «{product_name}» обновлены:\n{result}",
        reply_markup=admin_kb()
    )


@router.message(F.text == "🗑 Удалить товар")
async def delete_product_start(message: Message):
    if not is_admin_user(message.from_user):
        return

    products = list_all_products()
    if not products:
        await message.answer("Товаров нет.")
        return

    await message.answer("Выберите товар для удаления:", reply_markup=delete_products_kb())

@router.callback_query(F.data.startswith("delete_product:"))
async def delete_product_callback(callback: CallbackQuery):
    if not is_admin_user(callback.from_user):
        return

    product_id = int(callback.data.split(":")[1])
    delete_product(product_id)

    await callback.message.edit_text("Товар удалён.")
    await callback.answer()

@router.message(F.text == "📦 Все заказы")
async def all_orders(message: Message):
    if not is_admin_user(message.from_user):
        return

    dates = list_order_dates()
    if not dates:
        await message.answer("Заказов пока нет.")
        return

    await message.answer("Выберите день:", reply_markup=order_dates_kb())

@router.callback_query(F.data.startswith("orders_date:"))
async def orders_by_date(callback: CallbackQuery):
    if not is_admin_user(callback.from_user):
        return

    order_date = callback.data.split(":", 1)[1]
    orders = list_orders_by_date(order_date)

    if not orders:
        await callback.message.answer("Заказов за этот день нет.")
        await callback.answer()
        return

    await callback.message.answer(f"Заказы за {order_date}:")

    for order in orders:
        await callback.message.answer(render_order(order["id"]), reply_markup=order_admin_kb(order["id"]))

    await callback.answer()


@router.callback_query(F.data.startswith("order_confirm:") | F.data.startswith("web_confirm_order:"))
async def any_confirm_order_callback(callback: CallbackQuery):
    if not is_admin_user(callback.from_user):
        await callback.answer("Нет доступа.", show_alert=True)
        return

    order_id = parse_callback_id(callback.data)
    if not order_id:
        await callback.answer("Некорректная кнопка.", show_alert=True)
        return

    order = get_order(order_id)

    if not order:
        await callback.answer("Заказ не найден.", show_alert=True)
        return

    if order["status"] == "confirmed":
        await callback.answer("Заказ уже подтверждён.", show_alert=True)
        return

    if order["status"] == "cancelled":
        await callback.answer("Заказ уже отменён.", show_alert=True)
        return

    result = confirm_order(order_id)

    if not result:
        await callback.answer("Не удалось подтвердить заказ: проверь остатки или лимит промокода.", show_alert=True)
        return

    bonus_earned = int(result.get("bonus_earned", 0)) if isinstance(result, dict) else 0
    referral_reward = int(result.get("referral_reward", 0)) if isinstance(result, dict) else 0
    bonus_line = f"\nНачислено бонусов: +{bonus_earned}" if bonus_earned > 0 else ""
    referral_line = f"\nРеферальный бонус пригласившему: +{referral_reward}" if referral_reward > 0 else ""

    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    try:
        await callback.message.answer(f"✅ Заказ №{order_id} подтвержден{referral_line}")
    except Exception:
        pass

    try:
        await callback.bot.send_message(order["user_id"], f"✅ Заказ №{order_id} подтвержден.\n\nСпасибо за заказ!{bonus_line}")
    except Exception:
        pass

    await callback.answer("Заказ подтвержден")

@router.callback_query(F.data.startswith("order_cancel:") | F.data.startswith("web_cancel_order:"))
async def any_cancel_order_callback(callback: CallbackQuery):
    if not is_admin_user(callback.from_user):
        await callback.answer("Нет доступа.", show_alert=True)
        return

    order_id = parse_callback_id(callback.data)
    if not order_id:
        await callback.answer("Некорректная кнопка.", show_alert=True)
        return

    order = get_order(order_id)

    if not order:
        await callback.answer("Заказ не найден.", show_alert=True)
        return

    cancelled = cancel_order(order_id)

    if not cancelled:
        await callback.answer("Подтвержденный заказ нельзя отменить этой кнопкой.", show_alert=True)
        return

    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    try:
        await callback.message.answer(f"❌ Заказ №{order_id} отменён")
    except Exception:
        pass

    try:
        await callback.bot.send_message(order["user_id"], f"Ваш заказ №{order_id} отменён.")
    except Exception:
        pass

    await callback.answer("Заказ отменён")

@router.callback_query()
async def debug_unhandled_callback(callback: CallbackQuery):
    await callback.answer(f"Кнопка получена: {callback.data}", show_alert=True)
