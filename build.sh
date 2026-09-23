#!/usr/bin/env bash
# Скрипт сборки для Render (и любого другого PaaS)
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate --no-input
# Структура факультета без демо-контента; повторный запуск безопасен
python manage.py seed_portal --no-demo
