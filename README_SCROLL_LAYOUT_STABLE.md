Что исправлено:
1. Удалены конфликтующие CSS-блоки Android scroll fix / hard scroll fix / layout restore.
2. Удалён appScrollRef и внутренний fixed scroll-контейнер .app.
3. Скролл снова идёт нормально через документ/body, как было в стабильной версии.
4. Нижнее меню снова fixed у нижнего края реального экрана, а не в середине страницы.
5. .app больше не fixed, не transform, не height: var(--tg-viewport-height).
6. Для Android оставлен безопасный фикс: touch-action: pan-y на карточках товаров/категорий.
7. Для кнопок оставлен touch-action: manipulation, чтобы клики были быстрыми.
8. Добавлен padding-bottom, чтобы нижнее меню не перекрывало последние товары.
9. Скролл модалки товара сохранён отдельно через overflow-y:auto.

После деплоя на Android желательно полностью закрыть Telegram и открыть Mini App заново.
