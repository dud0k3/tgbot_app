Что исправлено:
1. Главная причина битых картинок: локальные картинки сохранялись в data/uploads, но FastAPI не раздавал папку /uploads.
2. Причина в коде: автопатч искал строку app = FastAPI(title="Shop Bot API"), а в проекте было app = FastAPI(title="SYNDICATE API"). Из-за этого app.mount('/uploads', ...) не вставился.
3. Теперь /uploads монтируется независимо от названия FastAPI-приложения.
4. Новые картинки из нового бота должны открываться как /uploads/filename.jpg.
5. Если локального файла нет, API пробует fallback через /api/tg-file?file_id=...
6. Добавлен debug endpoint /api/debug/uploads?token=DEBUG_TOKEN, чтобы видеть реальные файлы в data/uploads.

После деплоя:
1. Отправь /images_status.
2. Если локальных файлов 0 — выполни /cache_images или заново загрузите фото категории/товара.
3. Открой /api/debug/uploads?token=DEBUG_TOKEN и проверь, что files_count > 0.
