#!/usr/bin/env bash
# Run the packaged worker API and desktop GUI together.

set -euo pipefail

HOST="${WORKER_HOST:-0.0.0.0}"
PORT="${WORKER_PORT:-8000}"
API_URL="http://localhost:${PORT}/api/v1"
BACKEND_PID=""

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

cleanup() {
    echo ""
    echo -e "${YELLOW}Shutting down...${NC}"
    if [ -n "$BACKEND_PID" ] && kill -0 "$BACKEND_PID" 2>/dev/null; then
        kill "$BACKEND_PID" 2>/dev/null || true
        wait "$BACKEND_PID" 2>/dev/null || true
        echo -e "${GREEN}Backend stopped.${NC}"
    fi
}
trap cleanup EXIT

echo -e "${GREEN}Starting worker API on ${HOST}:${PORT}...${NC}"
WORKER_HOST="${HOST}" WORKER_PORT="${PORT}" fingerprint-worker-api &
BACKEND_PID=$!

MAX_WAIT=30
echo -n "Waiting for backend..."
for _ in $(seq 1 "$MAX_WAIT"); do
    if curl -s "${API_URL}/system/health" >/dev/null 2>&1; then
        echo ""
        echo -e "${GREEN}Backend is ready.${NC}"
        break
    fi
    echo -n "."
    sleep 1
done
echo ""

echo -e "${GREEN}Launching GUI...${NC}"
export WORKER_GUI_API_URL="${API_URL}"
fingerprint-worker-gui
