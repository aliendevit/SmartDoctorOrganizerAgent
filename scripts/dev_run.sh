#!/usr/bin/env bash
set -euo pipefail

if [[ ! -d ".venv" ]]; then
  python3 -m venv .venv
fi
source .venv/bin/activate

pip install --upgrade pip
if [[ -f "requirements.txt" ]]; then
  pip install -r requirements.txt
fi

export QT_AUTO_SCREEN_SCALE_FACTOR=1
export PYTHONUNBUFFERED=1

python main.py
