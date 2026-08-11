#!/bin/bash
# =============================================================================
# Launch backend + admin frontend + portal frontend for local development.
# =============================================================================
# Usage: ./dev/dev.sh
#
#   Backend:         http://localhost:8000  (SQLite; no Docker / MySQL needed)
#   Admin frontend:  http://localhost:5173
#   Portal frontend: http://localhost:5174
#
# Ctrl+C stops all three.
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [ -f "${SCRIPT_DIR}/backend/.venv/bin/python" ]; then
    PYTHON="${SCRIPT_DIR}/backend/.venv/bin/python"
elif command -v python3 &>/dev/null; then
    PYTHON=python3
else
    echo "Error: python3 not found. Create a venv in backend/ first."
    exit 1
fi

# Local dev always uses SQLite (Docker stack sets DB_ENGINE=mysql itself).
export DB_ENGINE=sqlite
# Do not enforce the Docker API key in plain local dev.
unset API_KEY

PIDS=()

cleanup() {
    echo ""
    echo "Stopping services..."
    for pid in "${PIDS[@]}"; do
        kill "$pid" 2>/dev/null || true
    done
    wait 2>/dev/null || true
    echo "All stopped."
}
trap cleanup EXIT INT TERM

echo "==> Backend     → http://localhost:8000  (SQLite)"
(cd "${SCRIPT_DIR}/backend" && "${PYTHON}" manage.py runserver) &
PIDS+=($!)

echo "==> Admin UI    → http://localhost:5173"
(cd "${SCRIPT_DIR}/admin-frontend" && npm run dev) &
PIDS+=($!)

echo "==> Portal UI   → http://localhost:5174"
(cd "${SCRIPT_DIR}/portal-frontend" && npm run dev) &
PIDS+=($!)

echo ""
echo "All services starting. Press Ctrl+C to stop."
wait
