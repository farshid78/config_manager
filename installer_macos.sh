#!/usr/bin/env bash
set -euo pipefail

# Installer for macOS
# Creates venv, installs requirements, creates data dirs.

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

log() { echo "[INFO] $*"; }
warn() { echo "[WARN] $*"; }
err() { echo "[ERROR] $*"; }

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    err "Missing command: $1"; exit 1;
  fi
}

require_cmd python3

if ! command -v pip >/dev/null 2>&1; then
  warn "pip not found. Trying to bootstrap with ensurepip ..."
  python3 -m ensurepip --upgrade || true
fi

# venv
if [[ ! -d "venv" ]]; then
  log "Creating virtual environment (venv) ..."
  python3 -m venv venv
fi

# shellcheck disable=SC1091
source venv/bin/activate

log "Upgrading pip ..."
pip install -U pip setuptools wheel

log "Installing Python dependencies ..."
pip install -r requirements.txt

log "Creating runtime directories ..."
mkdir -p data/logs data/exports data/clean_ips

if [[ ! -f .env ]]; then
  warn ".env not found. Creating from .env.example (if exists) ..."
  if [[ -f .env.example ]]; then
    cp .env.example .env
  else
    touch .env
  fi
  warn "Edit .env before starting if needed."
fi

log "Done. To start:"
echo "  source venv/bin/activate"
echo "  python main.py"

