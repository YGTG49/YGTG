#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$PROJECT_ROOT/.venv"

if [ ! -d "$VENV_DIR" ]; then
  python3 -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1090
source "$VENV_DIR/bin/activate"

pip install --upgrade pip >/dev/null
pip install -r "$PROJECT_ROOT/backend/requirements.txt"

export PYTHONPATH="$PROJECT_ROOT"
exec uvicorn backend.app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
