#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

start() {
  cd "$ROOT_DIR/backend"
  LOCAL_DEV_BYPASS_AUTH=1 ./cons_app_venv/bin/python3 -m uvicorn main:app --host 127.0.0.1 --port 8000
}

stop() {
  pkill -f "uvicorn main:app" || true
  if lsof -ti :8000 >/dev/null 2>&1; then
    kill -9 $(lsof -ti :8000)
  fi
}

rebuild() {
  cd "$ROOT_DIR"
  npm run build
  rm -rf backend/static
  mkdir -p backend/static
  cp -a out/. backend/static/
}

case "${1:-}" in
  start)
    start
    ;;
  stop)
    stop
    ;;
  rebuild)
    rebuild
    ;;
  *)
    echo "Usage: $0 {start|stop|rebuild}" >&2
    exit 1
    ;;
esac