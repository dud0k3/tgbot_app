# Добавь эти обработчики в handlers.py, если у тебя в уведомлениях Mini App используются кнопки:
# callback_data: web_confirm_order:<id>
# callback_data: web_cancel_order:<id>

from aiogram import F
from aiogram.types import CallbackQuery
from db import confirm_order, cancel_order

@router.callback_query(F.data.startswith("web_confirm_order:"))
async def web_confirm_order_callback(callback: CallbackQuery):
    order_id = int(callback.data.split(":", 1)[1])
    confirm_order(order_id)
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(f"✅ Заказ №{order_id} подтверждён")
    await callback.answer("Заказ подтверждён")

@router.callback_query(F.data.startswith("web_cancel_order:"))
async def web_cancel_order_callback(callback: CallbackQuery):
    order_id = int(callback.data.split(":", 1)[1])
    cancel_order(order_id)
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(f"❌ Заказ №{order_id} отменён")
    await callback.answer("Заказ отменён")
