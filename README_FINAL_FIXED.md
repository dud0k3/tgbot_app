# SYNDICATE v14 final fixed

Исправлено:
- кнопка «⬅️ Назад» всегда сбрасывает состояние и возвращает в главное меню;
- кнопка SYNDICATE из клавиатуры бота удалена;
- backend отдаёт приложение на `/`, а API остаётся на `/api/...`;
- бот + API запускаются в одном Docker-контейнере;
- товары списываются со склада только после подтверждения заказа админом;
- админ-кнопки подтверждения/отмены работают;
- заказы разделяются по дням;
- база не сбрасывается при Redeploy, если подключить сетевой диск `/data` и переменную `DB_PATH=/data/bot.db`.

## Dockhost variables

Добавить отдельными переменными:

```env
BOT_TOKEN=НОВЫЙ_ТОКЕН_ОТ_BOTFATHER
ADMINS=1364205492,861098409
ORDER_GROUP_ID=0
WEBAPP_URL=https://jr7p-h2em-cr2a.gw-1a.dockhost.net
DB_PATH=/data/bot.db
```

## Dockhost volume

Сетевой диск подключить к контейнеру:

```text
Mount path: /data
```

## Port and route

```text
Container port: 8000/TCP
Domain route path: /
Service: tgbot
Port: 8000
```
