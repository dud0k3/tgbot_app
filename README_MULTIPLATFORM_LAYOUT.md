Что сделано:
1. Добавлен единый viewport-manager для Telegram Mini App.
2. JS теперь определяет platform, fullscreen, safeAreaInset, contentSafeAreaInset, viewportHeight, visualViewport.height.
3. В CSS прокинуты переменные --tg-safe-top, --tg-safe-bottom-px, --app-height.
4. Приложение стало устойчивым для iPhone, Android, Desktop Telegram и обычного браузера.
5. .app работает как единый scroll-контейнер, что нужно для Android Telegram.
6. Нижняя навигация всегда фиксируется у физического низа экрана и учитывает safe-area.
7. Верхний контент учитывает Telegram fullscreen и больше не должен попадать под кнопки Telegram.
8. Карточка товара скроллится внутри productModal на Android и iOS.
9. Нижняя панель скрывается при открытой карточке товара, чтобы не перекрывать кнопку добавления.
10. Добавлены responsive-breakpoints для узких телефонов, обычных телефонов, планшетов/desktop preview.
11. Поля ввода имеют font-size 16px, чтобы iOS не зумил интерфейс.
12. Добавлена защита от переполнения текста и сеток.
13. Frontend успешно собран.

После деплоя обязательно проверить:
- iPhone Telegram fullscreen
- Android Telegram fullscreen
- Android Telegram non-fullscreen
- Desktop Telegram
- обычный браузер
