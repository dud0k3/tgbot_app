# Dockhost fast build fix

Исправление для зависания на шаге:

```text
RUN cd frontend && npm install
```

Что изменено:
- Dockerfile переведён на multi-stage build;
- frontend собирается в `node:20-alpine`;
- Python-контейнер больше не устанавливает node/npm через apt;
- убран `package-lock.json`, чтобы не тащить битые версии;
- React/ReactDOM зафиксированы на стабильной версии `18.2.0`;
- добавлен `.dockerignore`, чтобы Dockhost не отправлял мусор в сборку.

После загрузки на GitHub в Dockhost нужно нажать именно `Redeploy / Пересобрать`.
