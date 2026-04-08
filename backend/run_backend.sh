#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [ ! -d ".venv311" ]; then
  echo "Missing .venv311. Create it first:"
  echo "  macOS/Linux: python3.11 -m venv .venv311 && source .venv311/bin/activate && pip install -r requirements.txt"
  echo "  Windows:     py -3.11 -m venv .venv311 && .venv311\\Scripts\\activate && pip install -r requirements.txt"
  exit 1
fi

# Windows venv uses Scripts/; Unix uses bin/
if [ -x ".venv311/Scripts/python.exe" ]; then
  VENV_PYTHON=".venv311/Scripts/python.exe"
  ACTIVATE=".venv311/Scripts/activate"
elif [ -x ".venv311/bin/python" ]; then
  VENV_PYTHON=".venv311/bin/python"
  ACTIVATE=".venv311/bin/activate"
else
  echo "No Python found in .venv311 (expected Scripts/python.exe or bin/python)."
  exit 1
fi

# shellcheck source=/dev/null
source "$ACTIVATE"

free_port_8000() {
  local pids=""
  if command -v lsof >/dev/null 2>&1; then
    pids="$(lsof -ti tcp:8000 2>/dev/null || true)"
    if [ -n "$pids" ]; then
      echo "Stopping existing process(es) on port 8000: $pids"
      kill $pids 2>/dev/null || true
      sleep 1
    fi
    return 0
  fi
  if command -v powershell.exe >/dev/null 2>&1; then
    echo "Freeing port 8000 (if in use) via PowerShell..."
    powershell.exe -NoProfile -Command \
      'Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }' \
      || true
    sleep 1
  fi
}

free_port_8000

echo "Starting MindEase backend on http://0.0.0.0:8000"
exec "$VENV_PYTHON" -m uvicorn app.main:app --host 0.0.0.0 --port 8000
