#!/usr/bin/env bash
set -euo pipefail

ROOT="$(dirname "$(dirname "$(realpath "$0")")")"

echo "Installing backend dependencies..."
pip install -r "$ROOT/backend/requirements.txt"

echo "Building frontend..."
cd "$ROOT/frontend"
npm install
npm run build

echo "Copying built frontend into backend/static..."
python "$ROOT/scripts/prebuild_frontend.py"

echo "Build complete."
