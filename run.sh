#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env from .env.example. Edit it and rerun."
  exit 0
fi

python -m pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 127.0.0.1:8000
