Что исправлено:
1. Новые заказы снова отправляются админам для подтверждения.
2. Добавлен список admin_targets: бот запоминает админов, которые написали /start, /menu, /admin или открыли админку.
3. Уведомления теперь уходят в ADMINS, ORDER_GROUP_ID и сохраненным admin_targets.
4. Ошибки отправки больше не скрываются полностью: добавлен notification_log.
5. Добавлен endpoint /api/debug/notifications для проверки, куда бот пытался отправить заказ.
6. Добавлен endpoint /api/debug/status с targets/admins/order_group_id.
7. Если заказ не пришел админу, можно открыть /api/debug/notifications и увидеть причину.
