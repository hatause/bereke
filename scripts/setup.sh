#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -c 'import sys; assert sys.version_info >= (3,12), "Python 3.12+ required"'
python3 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements-dev.txt
(cd backend && ../.venv/bin/python -m alembic upgrade head && ../.venv/bin/python -m app.seed)
(cd frontend && npm ci)
