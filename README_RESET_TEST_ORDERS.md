Что добавлено:
1. Админская команда /reset_me_test — очищает тестовые данные текущего Telegram ID.
2. Админская команда /reset_user_test TELEGRAM_ID — очищает тестовые данные выбранного пользователя.
3. Удаляются orders, order_items, cart, bonus_transactions по пользователю и его заказам.
4. bonus_accounts не удаляется полностью: сохраняется referral_code, но balance=0, referrer_id=NULL, referral_bonus_paid=0.
5. Команды доступны только админу.
6. Для теста рефералки лучше использовать два разных Telegram-аккаунта: приглашающий и приглашённый.
