Что исправлено:
1. После включения Fullscreen в BotFather Telegram-кнопки сверху накладывались на кнопку корзины в баннере.
2. Добавлена поддержка Telegram safeAreaInset/contentSafeAreaInset.
3. JS записывает верхний safe-area в CSS-переменную --tg-safe-top.
4. .app получает padding-top с учётом fullscreen safe-area.
5. Верхняя кнопка корзины в hero-блоке дополнительно опущена ниже, чтобы не заезжать под кнопки Telegram.
6. Нижняя safe-area оставлена через env(safe-area-inset-bottom).
7. Скролл и остальная логика не менялись.

После деплоя нужно полностью закрыть Mini App и открыть заново, чтобы Telegram пересчитал safe-area.
