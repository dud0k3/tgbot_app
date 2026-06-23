Что исправлено:
1. Добавлен жёсткий фикс скролла для Telegram Android WebView.
2. body/html/root теперь не скроллятся — это важно для Android Telegram.
3. .app стала отдельным fixed scroll-контейнером с overflow-y:scroll.
4. Высота .app берётся из Telegram viewportHeight/viewportStableHeight через CSS-переменную --tg-viewport-height.
5. Свайп по карточкам товаров теперь разрешён: categoryCard/productCard/cleanProductCard имеют touch-action: pan-y.
6. Маленькие кнопки оставлены touch-action: manipulation, поэтому нажатия быстрые.
7. Добавлен ref на .app и маленькая активация scrollTop=1, чтобы Android WebView точно включил внутренний scroll.
8. Увеличен нижний padding, чтобы последние товары не скрывались за нижним меню и системной панелью Android.
9. Скролл модалки товара тоже переведён на внутренний scroll-контейнер.

После деплоя обязательно полностью закрыть Mini App и открыть заново на Android, а не просто обновить экран.
