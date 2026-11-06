#!/usr/bin/env bash
# SAARTHI one-command launcher (Linux/macOS). Uses MOCK_LLM=true by default.
set -e
cd "$(dirname "$0")"

echo "========================================"
echo " Starting SAARTHI Autonomous Resolution "
echo "========================================"

# 1. Backend deps (idempotent)
python -m pip install -q -r backend/requirements.txt || pip install -q -r backend/requirements.txt

# 2. Start backend on :8000
echo "[1/2] Starting Backend API on http://localhost:8000 ..."
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# 3. Start frontend on :5173
echo "[2/2] Starting Frontend UI on http://localhost:5173 ..."
cd frontend
if [ ! -d node_modules ]; then npm install --no-audit --no-fund; fi
npm run dev -- --port 5173 --host &
FRONTEND_PID=$!
cd ..

echo ""
echo "SAARTHI is running!"
echo "Customer Chat & Admin: http://localhost:5173"
echo "Backend API & Docs:    http://localhost:8000/docs"
echo "Press Ctrl+C to stop."
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT
wait
