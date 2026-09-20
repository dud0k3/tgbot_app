# Syndicate Bot

> Telegram-магазин с Mini App, каталогом товаров, корзиной, оформлением заказов, складским учётом и административной панелью.

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python\&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi\&logoColor=white)
![Aiogram](https://img.shields.io/badge/Aiogram-Telegram_Bot-2CA5E0?logo=telegram\&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Deployment-2496ED?logo=docker\&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-Database-003B57?logo=sqlite\&logoColor=white)

## О проекте

Syndicate Bot — Telegram-магазин, объединяющий Telegram-бота, Mini App и административную панель.

Пользователь может открыть каталог внутри Telegram, выбрать товар и его вариант, добавить позиции в корзину и оформить заказ. Администратор управляет товарами, категориями, остатками и заказами через отдельный интерфейс.

Проект реализован как полноценное клиент-серверное приложение и подготовлен к запуску в Docker.


## Реферальная система

Пользователь получает персональную реферальную ссылку. После оформления заказа приглашённым пользователем начисляется бонус в размере 2% от стоимости товаров.

Стоимость доставки и доплата за срочное оформление при расчёте бонуса не учитываются.

## Архитектура

```text
Пользователь Telegram
        │
        ├── Telegram Bot
        │       └── команды, уведомления и регистрация
        │
        └── Telegram Mini App
                └── каталог, корзина и оформление заказа
                         │
                         ▼
                    FastAPI API
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
        Бизнес-логика           База данных
        заказов и склада        пользователей,
                               товаров и заказов
```

## Технологии

### Backend

* Python 3.11;
* FastAPI;
* aiogram;
* SQLAlchemy;
* SQLite;
* Uvicorn.

### Frontend

* HTML;
* CSS;
* JavaScript;
* Telegram Web Apps API.

### Инфраструктура

* Docker;
* Docker Compose;
* переменные окружения через `.env`;
* healthcheck;
* постоянное хранилище данных.

## Структура проекта

```text
tgbot_app/
├── app/
│   ├── main.py           # запуск FastAPI и Telegram-бота
│   ├── api.py            # API для Mini App
│   ├── bot.py            # обработчики Telegram-бота
│   ├── auth.py           # проверка Telegram initData
│   ├── config.py         # конфигурация приложения
│   ├── db.py             # подключение к базе данных
│   ├── models.py         # модели SQLAlchemy
│   ├── services.py       # бизнес-логика
│   └── static/
│       ├── index.html    # интерфейс Mini App
│       ├── style.css
│       └── app.js
├── data/
├── .env.example
├── .gitignore
├──
```
