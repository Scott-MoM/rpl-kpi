#!/usr/bin/env bash
set -euo pipefail

echo "Installing backend dependencies..."
pip install -r requirements.txt

echo "Building frontend..."
cd frontend
npm install
npm run build
cd ..

echo "Copying built frontend into backend/static..."
python scripts/prebuild_frontend.py

echo "Build complete."
