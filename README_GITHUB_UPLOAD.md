# SYNDICATE Bot — GitHub-ready

Этот архив безопасен для GitHub:
- `.env` удалён;
- `bot.db` удалён;
- секреты и база добавлены в `.gitignore`.

## 1. После распаковки создай `.env`

```bash
cp .env.example .env
nano .env
```

Заполни:

```env
BOT_TOKEN=твой_новый_токен_от_BotFather
ADMINS=твой_telegram_id
ORDER_GROUP_ID=0
WEBAPP_URL=
```

## 2. Локальный запуск

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python bot.py
```

Backend:

```bash
source venv/bin/activate
uvicorn backend.api:app --reload --host 0.0.0.0 --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

## 3. Заливка на GitHub

```bash
git init
git branch -M main
git remote add origin https://github.com/dud0k3/tgbot_app.git
git add .
git commit -m "Upload bot project"
git push -u origin main
```

Если GitHub просит пароль — вставь Personal Access Token, не пароль от аккаунта.

## Важно

Если нужна старая база с товарами, положи `bot.db` вручную в корень проекта локально или на сервере. В GitHub её лучше не загружать.
