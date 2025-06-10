#!/usr/bin/env bash
# setup.sh – automatic environment setup for Target Assistant Bot

set -euo pipefail

# 1. Install system dependencies if apt is available
if command -v apt-get >/dev/null; then
  sudo apt-get update -y
  sudo apt-get install -y build-essential libssl-dev libffi-dev
fi

# 2. Create virtual environment
python3.12 -m venv .venv
source .venv/bin/activate

# 3. Upgrade pip and install requirements
python -m pip install --upgrade pip wheel
pip install --only-binary cryptography -r requirements.txt

# 4. Copy env file if not present
[ -f .env ] || cp env.example .env

# 5. Install pre-commit hooks (optional)
pre-commit install || true

# 6. Run tests
pytest --cov=. --cov-report=term --cov-fail-under=90
