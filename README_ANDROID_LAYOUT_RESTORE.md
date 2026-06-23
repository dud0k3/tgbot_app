Что исправлено:
1. После hardfix на Android скролл заработал, но нижняя навигация могла подниматься к середине экрана.
2. Причина: Telegram Android иногда отдаёт слишком маленький viewportHeight/viewportStableHeight.
3. Теперь JS берёт максимальную высоту из Telegram viewportHeight, window.innerHeight и visualViewport.height.
4. CSS для .app больше не опирается только на Telegram viewport variable: высота закреплена через 100vh/100dvh.
5. Нижняя панель снова fixed у нижнего края экрана.
6. Добавлен достаточный padding-bottom, чтобы карточки не прятались под нижней навигацией.
7. Скролл Android сохранён: .app остаётся внутренним scroll-контейнером.

После деплоя на Android нужно полностью закрыть Mini App и Telegram, потом открыть заново.
