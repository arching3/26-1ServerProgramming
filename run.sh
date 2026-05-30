#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

VENV_DIR=""

find_venv() {
    local candidates=(
        "$PROJECT_DIR/.venv"
        "$PROJECT_DIR/venv"
        "$PROJECT_DIR/../.venv"
        "$PROJECT_DIR/../venv"
        "$PROJECT_DIR/../../.venv"
        "$PROJECT_DIR/../../venv"
        "$PROJECT_DIR/backend/.venv"
        "$PROJECT_DIR/backend/venv"
        "$PROJECT_DIR/frontend/.venv"
        "$PROJECT_DIR/frontend/venv"
    )

    local candidate
    for candidate in "${candidates[@]}"; do
        if [[ -f "$candidate/bin/activate" ]]; then
            VENV_DIR="$(cd "$candidate" && pwd)"
            return 0
        fi
    done

    return 1
}

ensure_venv() {
    if find_venv; then
        echo "Using venv: $VENV_DIR"
        return 0
    fi

    VENV_DIR="$PROJECT_DIR/.venv"
    echo "No venv found within nearby project paths. Creating: $VENV_DIR"
    python3 -m venv "$VENV_DIR"
    # shellcheck source=/dev/null
    source "$VENV_DIR/bin/activate"
    python -m pip install --upgrade pip
    python -m pip install -r "$PROJECT_DIR/requirements.txt"
}

ensure_screen() {
    if ! command -v screen >/dev/null 2>&1; then
        echo "screen is required but not installed." >&2
        exit 1
    fi
}

restart_screen() {
    local name="$1"
    shift

    if screen -list | grep -q "[.]$name[[:space:]]"; then
        echo "Stopping existing screen session: $name"
        screen -S "$name" -X quit || true
    fi

    echo "Starting screen session: $name"
    screen -dmS "$name" bash -lc "$*"
}

ensure_venv
ensure_screen

mkdir -p "$PROJECT_DIR/logs"
touch "$PROJECT_DIR/logs/error.log"

ACTIVATE="source '$VENV_DIR/bin/activate'"

restart_screen "backend" \
    "cd '$PROJECT_DIR' && $ACTIVATE && uvicorn backend.main:app --host 127.0.0.1 --port 8000"

restart_screen "frontend" \
    "cd '$PROJECT_DIR' && $ACTIVATE && python frontend/app.py"

restart_screen "monitoring" \
    "cd '$PROJECT_DIR' && $ACTIVATE && tail -f logs/error.log"

cat <<EOF
Started services in screen sessions:
  backend    http://127.0.0.1:8000
  frontend   http://127.0.0.1:7860
  monitoring tail -f logs/error.log

Useful commands:
  screen -ls
  screen -r backend
  screen -r frontend
  screen -r monitoring
  screen -S backend -X quit
EOF
