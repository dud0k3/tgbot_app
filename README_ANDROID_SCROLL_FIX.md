Что исправлено:
1. Исправлен скролл Mini App на Android в Telegram WebView.
2. У .app убран overflow:hidden через финальный override: теперь overflow visible/overflow-x hidden.
3. Для html/body/#root явно включён overflow-y:auto и -webkit-overflow-scrolling:touch.
4. Убран жёсткий overscroll-behavior:none для вертикали: теперь overscroll-behavior-y:auto.
5. Добавлен touch-action:pan-y pinch-zoom для основных контейнеров, чтобы Android нормально принимал вертикальный свайп.
6. Для кнопок сохранён touch-action:manipulation, чтобы клики остались быстрыми.
7. Добавлен Telegram viewport handler: viewportHeight/viewportStableHeight записываются в CSS-переменную --tg-viewport-height.
8. При старте Mini App вызываются ready(), expand(), disableVerticalSwipes() если метод доступен.
9. Увеличен нижний padding, чтобы товары не прятались под нижней навигацией и системной Android-панелью.
10. Скролл модалки товара тоже исправлен для маленьких экранов.

Что проверить после деплоя:
1. Открыть Mini App на Android.
2. Перейти в категорию с товарами.
3. Пролистать ниже нижней навигации.
4. Открыть карточку товара и проверить скролл модалки.
