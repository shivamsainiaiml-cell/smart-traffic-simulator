#!/usr/bin/env bash
cd "$(dirname "$0")"
[ -d .venv ] || python3 -m venv .venv || { echo "Install Python 3.9+ first"; exit 1; }
source .venv/bin/activate
pip install -q -r requirements.txt
echo "Open http://127.0.0.1:5000 in your browser. Press Ctrl+C to stop."
python app.py
