import asyncio
import logging
import os
import sqlite3
import shutil
from datetime import datetime
from pathlib import Path
from time import monotonic

from aiogram import BaseMiddleware, Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, BotCommandScopeDefault, BotCommandScopeChat

from config import BOT_TOKEN, DB_PATH, ADMINS, ADMIN_USERNAMES
from db import init_db
from handlers import router

class RateLimitMiddleware(BaseMiddleware):
    def __init__(self, interval: float = 0.35):
        self.interval = interval
        self.last_action = {}

    async def __call__(self, handler, event, data):
        user = getattr(event, "from_user", None)
        if not user:
            return await handler(event, data)

        text = getattr(event, "text", "") or ""
        if "Назад" in text or text in {"/start", "start", "/menu", "/admin", "/id", "/cancel"}:
            return await handler(event, data)

        now = monotonic()
        last = self.last_action.get(user.id, 0)

        if now - last < self.interval:
            if hasattr(event, "answer"):
                try:
                    await event.answer("Слишком много действий. Подождите немного.")
                except Exception:
                    pass
            return

        self.last_action[user.id] = now
        return await handler(event, data)

async def backup_scheduler():
    backup_dir = DB_PATH.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)

    while True:
        try:
            if DB_PATH.exists():
                name = datetime.now().strftime("bot_%Y-%m-%d_%H-%M-%S.db")
                backup_path = backup_dir / name

                source = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
                destination = sqlite3.connect(backup_path)
                try:
                    source.backup(destination)
                finally:
                    destination.close()
                    source.close()

                backups = sorted(backup_dir.glob("bot_*.db"))
                for old_backup in backups[:-14]:
                    old_backup.unlink(missing_ok=True)

                logging.info("SQLite backup created")
        except Exception as e:
            logging.exception(f"Backup error: {e}")

        await asyncio.sleep(24 * 60 * 60)

async def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is empty. Add it to .env")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[
            logging.FileHandler("bot.log", encoding="utf-8"),
            logging.StreamHandler()
        ]
    )

    init_db()

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    await bot.delete_webhook(drop_pending_updates=False)

    public_commands = [
        BotCommand(command="start", description="Открыть магазин"),
        BotCommand(command="menu", description="Главное меню"),
        BotCommand(command="id", description="Показать мой Telegram ID"),
        BotCommand(command="cancel", description="Отменить текущее действие"),
    ]

    admin_commands = public_commands + [
        BotCommand(command="admin", description="Админ-меню"),
        BotCommand(command="edit_product", description="Редактировать товар"),
        BotCommand(command="promo", description="Управление промокодами"),
        BotCommand(command="stats", description="Статистика магазина"),
        BotCommand(command="stock", description="Склад и остатки товаров"),
        BotCommand(command="images_status", description="Проверить локальные картинки"),
        BotCommand(command="cache_images", description="Сохранить картинки локально"),
        BotCommand(command="reset_me_test", description="Очистить мои тестовые заказы"),
        BotCommand(command="reset_user_test", description="Полностью удалить тестового пользователя"),
        BotCommand(command="reset_user_set", description="Полностью удалить тестового пользователя"),
        BotCommand(command="ref_debug", description="Проверка рефералки пользователя"),
        BotCommand(command="ref_status", description="Статус реферальных начислений"),
        BotCommand(command="ref_pay", description="Начислить пропущенный реферальный бонус"),
    ]

    await bot.set_my_commands(public_commands, scope=BotCommandScopeDefault())

    for admin_id in ADMINS:
        try:
            await bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=int(admin_id)))
        except Exception as e:
            logging.warning(f"Could not set admin commands for {admin_id}: {e}")

    dp = Dispatcher(storage=MemoryStorage())
    dp.message.middleware(RateLimitMiddleware())
    dp.callback_query.middleware(RateLimitMiddleware())
    dp.include_router(router)

    asyncio.create_task(backup_scheduler())

    logging.info(f"ADMINS: {ADMINS}; ADMIN_USERNAMES: {sorted(ADMIN_USERNAMES)}")
    logging.info(f"HANDLERS FILE: {router}")
    logging.info("Bot started")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
