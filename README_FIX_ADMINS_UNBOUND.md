Что исправлено:
1. Бот падал при запуске с ошибкой UnboundLocalError: cannot access local variable 'ADMINS'.
2. Причина: внутри main() был повторный import ADMINS, из-за чего Python считал ADMINS локальной переменной.
3. Повторный import внутри main() убран.
4. ADMIN_USERNAMES теперь импортируется сверху вместе с ADMINS.
5. /cancel добавлен в исключения rate limiter, чтобы команда всегда срабатывала быстро.
6. Остальная логика не менялась.
