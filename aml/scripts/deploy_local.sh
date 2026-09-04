#!/usr/bin/env bash
# =============================================================================
# Mandol-AML local one-shot deploy + connectivity test (Linux / macOS / WSL)
# Usage:   bash aml/scripts/deploy_local.sh
# Env:     REPO_URL / WORK_DIR / BASE_URL / SKIP_INSTALL=1 / SKIP_TESTS=1
# =============================================================================
set -euo pipefail
REPO_URL="${REPO_URL:-https://github.com/bubaa9531-dh/Mandol.git}"
WORK_DIR="${WORK_DIR:-$PWD/Mandol-local}"
SKIP_INSTALL="${SKIP_INSTALL:-0}"
SKIP_TESTS="${SKIP_TESTS:-0}"

say(){ printf "\n[%s] %s\n" "$1" "$2"; }

say "1/5" "Fetch code -> $WORK_DIR"
if [ ! -d "$WORK_DIR/.git" ]; then
  git clone "$REPO_URL" "$WORK_DIR"
else
  git -C "$WORK_DIR" fetch --all --prune
  git -C "$WORK_DIR" checkout main 2>/dev/null || true
  git -C "$WORK_DIR" pull --ff-only origin main || true
fi
cd "$WORK_DIR"

say "2/5" "Check environment"
python3 --version
if ! command -v uv >/dev/null 2>&1; then
  echo "uv not found; installing via pip ..."
  python3 -m pip install --user uv
  export PATH="$HOME/.local/bin:$PATH"
fi
uv --version

say "3/5" "Install dependencies (uv sync --frozen --no-dev)"
if [ "$SKIP_INSTALL" != "1" ]; then uv sync --frozen --no-dev; fi

if [ "$SKIP_TESTS" != "1" ]; then
  say "3b/5" "Run unit tests"
  uv run pytest tests/ -q
fi

say "4/5" "Prepare .env (copy template if missing)"
[ -f .env ] || cp aml.env.example .env

say "5/5" "Run local end-to-end connectivity test"
uv run python aml/scripts/run_local_e2e.py

echo
echo "======================================================================"
echo " Local connectivity test PASSED: Add -> Search chain works."
echo " Next: set Memory System Key -> platform Smoke -> Full evaluation."
echo "======================================================================"
