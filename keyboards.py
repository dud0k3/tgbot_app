from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove


def main_keyboard(is_admin=False, webapp_url=None):
    if not is_admin:
        return ReplyKeyboardRemove(remove_keyboard=True)

    rows = [
        [KeyboardButton(text="🛍 Товары"), KeyboardButton(text="🛒 Корзина")],
        [KeyboardButton(text="📦 Мои заказы"), KeyboardButton(text="💬 Поддержка")],
        [KeyboardButton(text="⚙️ Админка")]
    ]

    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def admin_keyboard():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="➕ Добавить товар"), KeyboardButton(text="➕ Категория")],
        [KeyboardButton(text="✏️ Редактировать категорию"), KeyboardButton(text="📦 Все заказы")],
        [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="🏬 Склад")],
        [KeyboardButton(text="⬅️ Назад")]
    ], resize_keyboard=True)


def order_admin_keyboard(order_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"web_confirm_order:{order_id}"),
            InlineKeyboardButton(text="❌ Отменить", callback_data=f"web_cancel_order:{order_id}")
        ]
    ])
