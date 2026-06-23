# SYNDICATE TG App v2

## Что исправлено

- Кнопки стали обычными активными элементами.
- Дизайн полностью переделан в фиолетовом стиле.
- Frontend ходит в backend через `/api`, Vite сам проксирует запросы.
- Картинки категорий и товаров берутся по Telegram `file_id` через backend.
- Заказ из Mini App отправляет уведомление админам в Telegram.

## Как установить

Распакуй архив в папку бота с заменой папок:

```text
simple_shop_bot/
  bot.db
  .env
  backend/
  frontend/
```

## 1. Backend

```bash
cd ~/Desktop/simple_shop_bot/backend
source venv/bin/activate
pip install -r requirements.txt
uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

Проверка:

```text
http://127.0.0.1:8000/api/categories
```

## 2. Frontend

Во втором терминале:

```bash
cd ~/Desktop/simple_shop_bot/frontend
npm install
npm run dev
```

## 3. Ngrok

В третьем терминале:

```bash
ngrok http 5173
```

Ссылку ngrok оставляешь в BotFather.

## Важно

Если фото всё равно не отображаются:
1. Проверь, что в `.env` есть BOT_TOKEN.
2. Проверь backend: `http://127.0.0.1:8000/api/categories`.
3. У категории или товара должен быть сохранён `image_id` / `photo_id`.
