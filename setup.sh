#!/usr/bin/env bash
# One-shot local setup script for MF Intelligence (macOS / Linux / WSL).
# Usage:
#   ./setup.sh         # install + create .env files (interactive secret gen)
#   ./setup.sh start   # also start backend + frontend in two background windows

set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
echo "==> Project root: $ROOT"

# --- Backend env ---
if [ ! -f "$ROOT/backend/.env" ]; then
  echo "==> Creating backend/.env from template"
  cp "$ROOT/backend/.env.example" "$ROOT/backend/.env"
  SECRET=$(python3 -c "import secrets;print(secrets.token_hex(32))")
  # macOS sed needs '' arg; use portable form
  sed -i.bak "s|replace-me-with-a-64-char-hex-secret|$SECRET|" "$ROOT/backend/.env" && rm "$ROOT/backend/.env.bak"
  echo "    JWT_SECRET generated automatically."
fi

# --- Frontend env ---
if [ ! -f "$ROOT/frontend/.env" ]; then
  echo "==> Creating frontend/.env from template"
  cp "$ROOT/frontend/.env.example" "$ROOT/frontend/.env"
fi

# --- Backend deps ---
echo "==> Installing backend Python deps..."
cd "$ROOT/backend"
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install --upgrade pip > /dev/null
pip install --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/ -r requirements.txt
deactivate

# --- Frontend deps ---
echo "==> Installing frontend deps (yarn)..."
cd "$ROOT/frontend"
if ! command -v yarn >/dev/null 2>&1; then
  echo "ERROR: yarn not found. Install with: npm install -g yarn"
  exit 1
fi
yarn install

cd "$ROOT"

# --- Mongo check ---
if ! command -v mongod >/dev/null 2>&1 && ! command -v mongosh >/dev/null 2>&1; then
  echo "WARNING: MongoDB CLI not detected on PATH."
  echo "  Install: https://www.mongodb.com/docs/manual/installation/"
  echo "  Or use docker: docker run -d -p 27017:27017 --name mongo mongo:7"
fi

cat <<EOF

==> Setup complete.

Next steps:
  1. (Optional) Edit backend/.env and add RESEND_API_KEY / EMERGENT_LLM_KEY
  2. Start MongoDB (e.g.  docker run -d -p 27017:27017 --name mongo mongo:7)
  3. Start backend:
       cd backend && source .venv/bin/activate && uvicorn server:app --reload --port 8001
  4. Start frontend (separate terminal):
       cd frontend && yarn start
  5. Visit http://localhost:3000  (admin@mfintel.com / Admin@12345)

Or use Docker:
  docker compose up --build
EOF
