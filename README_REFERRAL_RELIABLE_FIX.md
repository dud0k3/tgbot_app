Что исправлено:
1. Реферальный start_param теперь передаётся надёжнее: backend берёт его из подписанного initData, а frontend дополнительно отправляет X-Referral-Start-Param.
2. Frontend сохраняет start_param в localStorage при первом открытии по ссылке и отправляет его во всех API-запросах.
3. Это исправляет ситуацию, когда пользователь открыл Mini App по реферальной ссылке, но Telegram-клиент не передал start_param в обычном initData на последующих запросах.
4. Добавлена команда /ref_debug TELEGRAM_ID — показывает, есть ли у приглашённого referrer_id и что произошло с заказами/бонусами.
5. Добавлена команда /reset_ref_test REFERRER_ID INVITED_USER_ID — для теста заново привязывает приглашённого к пригласившему и сбрасывает referral_bonus_paid.
6. Добавлен endpoint /api/debug/referral/{user_id}.
7. Новую антифрод-систему не добавлял. Это исправление основано на стабильной версии syndicate_fix_500_order + reset commands.
