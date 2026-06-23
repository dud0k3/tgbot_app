Что исправлено:
1. По скрину видно: у приглашённого referrer_id=None, order.referrer=0, referral_links пустой. Значит Mini App не получил/не сохранил start_param.
2. Direct Mini App ссылки startapp на части клиентов Telegram не всегда стабильно передают start_param.
3. Поэтому основная реферальная ссылка теперь ведёт через обычный /start: https://t.me/BOT?start=ref_CODE.
4. Бот получает payload /start ref_CODE, сразу сохраняет referrer_id в базе, затем показывает кнопку открытия Mini App.
5. Теперь referrer_id фиксируется ДО заказа, не зависит от Telegram WebApp start_param.
6. Прямая Mini App ссылка сохранена как app_referral_link, но referral_link в BONUS теперь надёжная bot-start ссылка.
7. Добавлена команда /ref_bind INVITED_USER_ID REF_CODE для ручной привязки, если пользователь уже пришёл по старой ссылке.
8. После ручной привязки можно начислить за уже подтверждённый заказ командой /ref_pay ORDER_ID REFERRER_ID.
9. Новую антифрод-систему не добавлял.
