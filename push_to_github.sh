#!/usr/bin/env bash
set -e

git init
git branch -M main
git remote remove origin 2>/dev/null || true
git remote add origin https://github.com/dud0k3/tgbot_app.git
git add .
git commit -m "Upload final Syndicate v14 all requests" || true
git push -f origin main
