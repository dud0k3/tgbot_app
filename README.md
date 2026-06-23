# JOOT VPN

Простой Telegram VPN-бот и Mini App: клиент нажимает одну кнопку и получает одну subscription-ссылку, внутри которой доступны все протоколы из выбранных 3x-ui inbound.

## Что работает

- команды бота `/start`, `/connect`, `/subscriptions`, `/profile`, `/help`;
- выдача VPN по кнопке без оплаты;
- одна подписка на одного пользователя;
- лимит до 3 устройств;
- добавление клиента сразу во все `XUI_INBOUND_IDS`;
- единый `subId`, чтобы 3x-ui subscription отдавала все протоколы одной ссылкой;
- Mini App в стиле JOOT Matte: чёрный, белый, синий, матовый минимализм;
- профиль, копирование ссылки, обновление конфига;
- админ-вкладка для владельца;
- SQLite/PostgreSQL, Docker, healthcheck.

## Быстрый запуск

```bash
cp .env.example .env
docker compose up -d --build
curl http://localhost:8000/health
```

## Основные переменные

```env
BOT_TOKEN=токен_от_BotFather
APP_URL=https://домен-приложения
ADMIN_IDS=ваш_telegram_id
DATABASE_URL=sqlite:///./data/joot.db
BOT_MODE=polling
DEV_MODE=false
```

## 3x-ui

В 3x-ui заранее создай и проверь рабочие inbounds. Для твоей текущей схемы это примерно:

```text
ID 1: VLESS / TCP / Reality / 13877
ID 3: Trojan / TCP / Reality / 42024
ID 4: VLESS / XHTTP / TLS / 23024
ID 5: VLESS / TCP / Reality / 443
ID 6: VLESS / TCP / TLS / 57272
```

В `.env` укажи эти ID:

```env
VPN_PROVIDER=3xui
XUI_BASE_URL=https://messi.ohbah.com:54892/YOUR_WEB_BASE_PATH
XUI_API_TOKEN=API_TOKEN_ИЗ_3X_UI
XUI_INBOUND_IDS=1,3,4,5,6
XUI_VERIFY_SSL=true
XUI_SUB_URL_TEMPLATE=https://messi.ohbah.com:2096/api/v1/profile/sync/{sub_id}
XUI_CLIENT_LIMIT_IP=3
DEFAULT_SUBSCRIPTION_DEVICES=3
```

`XUI_INBOUND_IDS` определяет, какие протоколы попадут в одну подписку. Бот создаёт одного клиента `tg_<telegram_id>` во всех этих inbound с одинаковым `subId`.

Для VLESS TCP Reality backend ставит `flow=xtls-rprx-vision`. Для VLESS TLS, XHTTP и Trojan flow не ставится, чтобы не ломать конфиг.

## Команды бота

```text
/start — 🚀 Запустить бота
/connect — 🔐 Подключить VPN
/subscriptions — 🌍 Подписки
/profile — 👤 Профиль
/help — ❓ Помощь
```

## Локальная проверка Mini App

```env
DEV_MODE=true
ADMIN_IDS=123456789
```

Открыть:

```text
http://localhost:8000/?dev_id=123456789
```

## Безопасность

Не публикуй `.env`, `BOT_TOKEN`, `XUI_API_TOKEN`, логин/пароль панели, приватные ключи Reality и root-пароль.
