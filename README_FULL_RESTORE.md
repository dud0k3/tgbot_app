# SYNDICATE — полностью восстановленная сборка

Собрано из:
- твоего архива `syndicate_tg_app_v14_bottom_nav_clean`;
- оригинальных файлов бота: `bot.py`, `handlers.py`, `db.py`, `config.py`, `keyboards.py`;
- твоей базы `bot.db`.

## Что восстановлено

- Telegram-бот с админкой.
- Добавление категорий.
- Добавление картинок к категориям.
- Добавление товаров.
- Добавление фото к товарам.
- Корзина.
- Оформление заказов.
- Подтверждение/отмена заказов.
- Статистика.
- Telegram Mini App с дизайном v14.
- Backend API для Mini App.
- Картинки товаров и категорий в Mini App.
- Поддержка `@guapsyndicate`.
- Dockerfile и supervisord для Dockhost.

## Важно

В `.env` нужно вставить новый токен от BotFather.

Создай `.env`:

```bash
cp .env.example .env
nano .env
```

Пример:

```env
BOT_TOKEN=1234567890:AA...
ADMINS=1364205492,861098409
ORDER_GROUP_ID=0
WEBAPP_URL=
```

## Локальный запуск

### 1. Установить зависимости

```bash
cd ~/Desktop/simple_bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Запустить бота

```bash
python bot.py
```

### 3. Запустить backend

Во втором терминале:

```bash
cd ~/Desktop/simple_bot
source venv/bin/activate
uvicorn backend.api:app --reload --host 0.0.0.0 --port 8000
```

Проверка:

```text
http://localhost:8000/api/health
```

### 4. Запустить frontend

В третьем терминале:

```bash
cd ~/Desktop/simple_bot/frontend
npm install
npm run dev
```

Откроется:

```text
http://localhost:5174
```

### 5. Открыть в Telegram Mini App

В четвёртом терминале:

```bash
ngrok http 5174
```

Скопируй HTTPS-ссылку и вставь в `.env`:

```env
WEBAPP_URL=https://xxxxx.ngrok-free.app
```

Перезапусти бота:

```bash
python bot.py
```

Потом в Telegram:

```text
/start
→ SYNDICATE
```

## Как добавить фото товара

```text
/start
→ ⚙️ Админка
→ ➕ Добавить товар
→ выбрать категорию
→ название
→ описание
→ цена
→ количество
→ отправить фото
```

Фото нужно отправлять именно как фотографию, не как файл.
