#!/usr/bin/env bash
# DorkHub installer for Linux / macOS.
# Sets up the Python backend, builds the frontend, creates .env, and asks for
# the login password during install. Re-runnable: it won't overwrite an existing
# .env unless you confirm.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"
ENV_FILE="$ROOT/.env"
PY="${PYTHON:-python3}"

say()  { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m!  \033[0m %s\n' "$*"; }
die()  { printf '\033[1;31mxx \033[0m %s\n' "$*" >&2; exit 1; }

# ---------- prerequisites ----------
command -v "$PY" >/dev/null 2>&1 || die "Python 3 not found. Install Python 3.12+ and retry."
PYVER=$("$PY" -c 'import sys; print("%d.%d" % sys.version_info[:2])')
say "Using Python $PYVER"
command -v node >/dev/null 2>&1 || warn "Node.js not found. The web UI build will be skipped."
command -v npm  >/dev/null 2>&1 || true

# ---------- backend venv + deps ----------
say "Creating virtual environment and installing backend dependencies..."
cd "$BACKEND"
"$PY" -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
say "Backend dependencies installed."

# ---------- password prompt ----------
PW=""
PW2="x"
while [ "$PW" != "$PW2" ] || [ -z "$PW" ]; do
  printf "Set DorkHub login password: "
  read -rs PW; echo
  printf "Confirm password: "
  read -rs PW2; echo
  [ "$PW" = "$PW2" ] || warn "Passwords do not match, try again."
  [ -n "$PW" ] || warn "Password cannot be empty."
done

say "Hashing password..."
HASH=$(printf '%s\n' "$PW" | python -m app.cli hash-password)
SECRET=$(python -m app.cli gen-secret)
unset PW PW2

# ---------- write .env ----------
cd "$ROOT"
write_env=true
if [ -f "$ENV_FILE" ]; then
  printf ".env already exists. Overwrite password + secret in it? [y/N] "
  read -r ans
  case "$ans" in
    y|Y) write_env=update ;;
    *)   write_env=false; warn "Keeping existing .env unchanged." ;;
  esac
fi

if [ "$write_env" = "true" ]; then
  cp .env.example "$ENV_FILE"
  # portable in-place edit
  "$PY" - "$ENV_FILE" "$HASH" "$SECRET" <<'PYEOF'
import sys
path, h, s = sys.argv[1], sys.argv[2], sys.argv[3]
lines = open(path).read().splitlines()
out = []
for ln in lines:
    if ln.startswith("DORKHUB_AUTH_PASSWORD_HASH="):
        out.append("DORKHUB_AUTH_PASSWORD_HASH=" + h)
    elif ln.startswith("DORKHUB_SECRET_KEY="):
        out.append("DORKHUB_SECRET_KEY=" + s)
    else:
        out.append(ln)
open(path, "w").write("\n".join(out) + "\n")
PYEOF
  say "Wrote $ENV_FILE"
elif [ "$write_env" = "update" ]; then
  "$PY" - "$ENV_FILE" "$HASH" "$SECRET" <<'PYEOF'
import sys
path, h, s = sys.argv[1], sys.argv[2], sys.argv[3]
lines = open(path).read().splitlines()
seen_h = seen_s = False
out = []
for ln in lines:
    if ln.startswith("DORKHUB_AUTH_PASSWORD_HASH="):
        out.append("DORKHUB_AUTH_PASSWORD_HASH=" + h); seen_h = True
    elif ln.startswith("DORKHUB_SECRET_KEY="):
        out.append("DORKHUB_SECRET_KEY=" + s); seen_s = True
    else:
        out.append(ln)
if not seen_h: out.append("DORKHUB_AUTH_PASSWORD_HASH=" + h)
if not seen_s: out.append("DORKHUB_SECRET_KEY=" + s)
open(path, "w").write("\n".join(out) + "\n")
PYEOF
  say "Updated password + secret in $ENV_FILE"
fi
unset HASH SECRET

# ---------- db + dorks ----------
cd "$BACKEND"
say "Initializing database and importing the dork library..."
python -m app.cli initdb
python -m app.cli import-dorks

# ---------- frontend build ----------
if command -v npm >/dev/null 2>&1; then
  say "Installing and building the web UI..."
  cd "$FRONTEND"
  npm install --silent
  npm run build --silent
  say "Web UI built into backend/static."
else
  warn "npm not available; skipped UI build. Install Node.js 20+ then run: cd frontend && npm install && npm run build"
fi

cat <<EOF

$(say "Installation complete.")

To start DorkHub:

  cd backend
  source .venv/bin/activate
  uvicorn app.main:app --host 0.0.0.0 --port 8000

Then open http://localhost:8000 and sign in with your password.

Before running real searches, add a provider key to .env
(DORKHUB_SERPER_API_KEY or DataForSEO credentials).
EOF
