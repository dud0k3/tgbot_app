# SYNDICATE TG App v13 — комфорт магазина + backend

Сделано:
1. Убрано дублирование категорий: в каталоге остаются карточки, в товарах — только горизонтальные табы.
2. Добавлена подробная карточка товара по нажатию.
3. В корзине добавлены кнопки `− / +` для количества.
4. Добавлен счётчик товаров в корзине сверху и в нижнем меню.
5. Backend проверяет Telegram `initData` через `X-Telegram-Init-Data`.
6. В уведомлении админу добавлены inline-кнопки:
   - Подтвердить
   - Отменить
   - Написать клиенту

Замени:
```text
backend/api.py
frontend/src/App.jsx
frontend/src/style.css
```

Важно:
- Для кнопок подтверждения заказа из уведомления добавь код из:
```text
backend/HANDLERS_PATCH.py
```
в конец своего `handlers.py`, если такие callback ещё не обработаны.

Запуск:
```bash
cd ~/Desktop/simple_shop_bot/backend
uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

```bash
cd ~/Desktop/simple_shop_bot/frontend
npm install
npm run dev
```
