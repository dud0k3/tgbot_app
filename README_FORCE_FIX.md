# FORCE FIX: остатки и кнопки заказов

## Что исправлено

1. Mini App больше НЕ списывает товар при создании заказа.
2. Товар остаётся в каталоге до подтверждения админом.
3. Списание происходит только при нажатии `✅ Подтвердить`.
4. Кнопки поддерживают оба формата:
   - `order_confirm:<id>`
   - `web_confirm_order:<id>`
   - `order_cancel:<id>`
   - `web_cancel_order:<id>`
5. В терминале бота будет печататься:
   - `ADMIN BUTTON CLICK: ...`
   - или `UNHANDLED CALLBACK: ...`

## Важно

Нужно заменить именно эти файлы:
- `backend/api.py`
- `handlers.py`
- `bot.py`

И потом обязательно убить старый процесс бота:

```bash
pkill -f bot.py
```

Потом запустить заново:

```bash
cd ~/Desktop/simple_bot
source venv/bin/activate
python bot.py
```

Backend тоже перезапустить:

```bash
cd ~/Desktop/simple_bot
source venv/bin/activate
uvicorn backend.api:app --reload --host 0.0.0.0 --port 8000
```

## Проверка

После нажатия на кнопку `✅ Подтвердить` в терминале с ботом должно появиться:

```text
ADMIN BUTTON CLICK: web_confirm_order:5
```

Если этого нет — ты нажимаешь кнопку от старого процесса/другого бота или запущен не тот `handlers.py`.

## Если товар уже списался старым кодом

```bash
python restore_stock_from_order.py 5
```

Где `5` — номер заказа.
