Что исправлено:
1. Предыдущий body-scroll вариант не работал на Android Telegram.
2. Теперь body полностью заблокирован, а скролл вынесен в .app.
3. .app сделан fixed-контейнером через top/bottom/left/right, но БЕЗ transform.
4. Именно transform ломал fixed bottomNav и поднимал меню в середину экрана.
5. bottomNav снова fixed относительно viewport и стоит внизу.
6. На карточках товаров/категорий стоит touch-action: pan-y, чтобы Android принимал вертикальный свайп.
7. На маленьких кнопках оставлен touch-action: manipulation.
8. Добавлен большой padding-bottom, чтобы последний товар не прятался под меню.
9. Скролл карточки товара в модалке сохранён.
10. Удалены остатки appScrollRef/hardfix JS, чтобы не было конфликтов.
