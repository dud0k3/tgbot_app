Что сделано:
1. Команда /reset_user_test TELEGRAM_ID теперь полностью удаляет пользователя из бота.
2. Добавлен алиас /reset_user_set TELEGRAM_ID, как ты написал в сообщении.
3. Удаляется users.
4. Удаляется bonus_accounts, включая balance, referral_code, referrer_id, referral_bonus_paid.
5. Удаляются orders пользователя и order_items по этим заказам.
6. Удаляется cart пользователя.
7. Удаляются все bonus_transactions пользователя и транзакции по его заказам.
8. Удаляются referral_links, где пользователь был приглашённым или пригласившим.
9. У других пользователей очищается referrer_id, если он ссылался на удаляемого пользователя.
10. У чужих заказов referrer_id удаляемого пользователя сбрасывается в 0.
11. Удаляется admin_targets для этого ID.
12. После команды пользователь для системы выглядит так, будто никогда не заходил в бота/Mini App.

Команды:
/reset_user_test TELEGRAM_ID
/reset_user_set TELEGRAM_ID
/reset_me_test
