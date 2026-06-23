from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message, WebAppInfo
from .config import get_settings
from .db import SessionLocal
from .services import active_subscription, provision_default_subscription, upsert_user
from . import models


settings = get_settings()
bot = Bot(settings.bot_token) if settings.bot_token else None
dp = Dispatcher()
router = Router()
dp.include_router(router)


def main_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="🔐 Подключить VPN", callback_data="connect")],
    ]
    if settings.app_url:
        rows.append([InlineKeyboardButton(text="🌐 Открыть приложение", web_app=WebAppInfo(url=settings.app_url))])
    rows.append([
        InlineKeyboardButton(text="👤 Профиль", callback_data="profile"),
        InlineKeyboardButton(text="❓ Помощь", callback_data="help"),
    ])
    if settings.support_username:
        rows.append([InlineKeyboardButton(text="Поддержка", url=f"https://t.me/{settings.support_username.lstrip('@')}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def access_keyboard(url: str | None = None) -> InlineKeyboardMarkup:
    rows = []
    if url:
        rows.append([InlineKeyboardButton(text="🔗 Открыть подписку", url=url)])
    if settings.app_url:
        rows.append([InlineKeyboardButton(text="🌐 Открыть приложение", web_app=WebAppInfo(url=settings.app_url))])
    rows.append([InlineKeyboardButton(text="❓ Инструкция", callback_data="help")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def sub_text(sub: models.Subscription) -> str:
    traffic = "безлимит" if not sub.traffic_gb else f"{sub.traffic_gb} ГБ"
    return (
        "<b>JOOT VPN</b>\n\n"
        "Подписка активна.\n"
        f"Устройства: до {sub.devices}\n"
        f"Трафик: {traffic}\n\n"
        "Одна ссылка содержит все доступные протоколы.\n\n"
        f"<code>{sub.access_url}</code>"
    )


async def send_connect(target: Message | CallbackQuery) -> None:
    msg = target.message if isinstance(target, CallbackQuery) else target
    with SessionLocal() as db:
        user_data = target.from_user.model_dump()
        user = upsert_user(db, user_data)
        try:
            sub = await provision_default_subscription(db, user)
        except Exception as error:
            text = str(error).strip() or type(error).__name__
            await msg.answer(f"Не удалось создать VPN-доступ.\n\n{text}", reply_markup=main_keyboard())
            if isinstance(target, CallbackQuery):
                await target.answer("Ошибка выдачи", show_alert=True)
            return
    await msg.answer(sub_text(sub), parse_mode="HTML", reply_markup=access_keyboard(sub.access_url))
    if isinstance(target, CallbackQuery):
        await target.answer("VPN готов")


async def send_subscription(target: Message | CallbackQuery) -> None:
    msg = target.message if isinstance(target, CallbackQuery) else target
    with SessionLocal() as db:
        user = upsert_user(db, target.from_user.model_dump())
        sub = active_subscription(db, user.id)
    if not sub:
        await msg.answer("Активной подписки пока нет. Нажмите «Подключить VPN».", reply_markup=main_keyboard())
        if isinstance(target, CallbackQuery):
            await target.answer()
        return
    await msg.answer(sub_text(sub), parse_mode="HTML", reply_markup=access_keyboard(sub.access_url))
    if isinstance(target, CallbackQuery):
        await target.answer()


async def send_profile(target: Message | CallbackQuery) -> None:
    msg = target.message if isinstance(target, CallbackQuery) else target
    with SessionLocal() as db:
        user = upsert_user(db, target.from_user.model_dump())
        sub = active_subscription(db, user.id)
    status = "активна" if sub else "нет активной подписки"
    devices = sub.devices if sub else settings.default_subscription_devices
    text = (
        "<b>Профиль JOOT</b>\n\n"
        f"Telegram ID: <code>{user.telegram_id}</code>\n"
        f"Статус: {status}\n"
        f"Устройства: до {devices}\n"
    )
    await msg.answer(text, parse_mode="HTML", reply_markup=main_keyboard())
    if isinstance(target, CallbackQuery):
        await target.answer()


async def send_help(target: Message | CallbackQuery) -> None:
    msg = target.message if isinstance(target, CallbackQuery) else target
    text = (
        "<b>Как подключиться</b>\n\n"
        "1. Нажмите «Подключить VPN».\n"
        "2. Скопируйте ссылку подписки.\n"
        "3. Добавьте её в Happ или Hiddify.\n\n"
        "Одна подписка включает все доступные протоколы и работает максимум на 3 устройствах."
    )
    await msg.answer(text, parse_mode="HTML", reply_markup=main_keyboard())
    if isinstance(target, CallbackQuery):
        await target.answer()


@router.message(CommandStart())
async def start(message: Message) -> None:
    with SessionLocal() as db:
        upsert_user(db, message.from_user.model_dump())
    await message.answer(
        "<b>JOOT VPN</b>\n\nОдна подписка. Все протоколы. До 3 устройств.",
        parse_mode="HTML",
        reply_markup=main_keyboard(),
    )


@router.message(Command("connect"))
async def connect(message: Message) -> None:
    await send_connect(message)


@router.message(Command("subscriptions"))
async def subscriptions(message: Message) -> None:
    await send_subscription(message)


@router.message(Command("profile"))
async def profile(message: Message) -> None:
    await send_profile(message)


@router.message(Command("help"))
async def help_command(message: Message) -> None:
    await send_help(message)


@router.message(Command("app"))
async def open_app(message: Message) -> None:
    await message.answer("Открыть JOOT VPN:", reply_markup=main_keyboard())


@router.message(Command("link"))
async def vpn_link(message: Message) -> None:
    await send_subscription(message)


@router.callback_query(F.data == "connect")
async def connect_callback(callback: CallbackQuery) -> None:
    await send_connect(callback)


@router.callback_query(F.data == "profile")
async def profile_callback(callback: CallbackQuery) -> None:
    await send_profile(callback)


@router.callback_query(F.data == "help")
async def help_callback(callback: CallbackQuery) -> None:
    await send_help(callback)
