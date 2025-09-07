#!/usr/bin/env bash
set -euo pipefail

APP_NAME="MedicalDocAI"
ENTRY="main.py"
ICON="resources/icons/app.icns"   # optional
DIST_DIR="dist"
SPEC_FILE="main.spec"             # if present; else PyInstaller cmd below builds one

# Ensure venv
if [[ ! -d ".venv" ]]; then
  python3 -m venv .venv
fi
source .venv/bin/activate

pip install --upgrade pip wheel setuptools
if [[ -f "requirements.txt" ]]; then
  pip install -r requirements.txt
fi
# reportlab and PyQt5 already in requirements typically; ensure pyinstaller
pip install pyinstaller

# Clean previous build
rm -rf build "${DIST_DIR}/${APP_NAME}.app"

if [[ -f "${SPEC_FILE}" ]]; then
  pyinstaller "${SPEC_FILE}"
else
  pyinstaller --noconfirm \
    --name "${APP_NAME}" \
    --windowed \
    --add-data "resources:resources" \
    --add-data "json:json" \
    --hidden-import "reportlab" \
    "${ENTRY}"
fi

echo "Built app at ${DIST_DIR}/${APP_NAME}.app"

# Optional: create a DMG (requires create-dmg)
if command -v create-dmg >/dev/null 2>&1; then
  DMG="${DIST_DIR}/${APP_NAME}.dmg"
  rm -f "$DMG"
  create-dmg "$DMG" "${DIST_DIR}/${APP_NAME}.app"
  echo "DMG created at $DMG"
else
  echo "create-dmg not found; skipping DMG creation."
fi
