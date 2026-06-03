#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

echo "============================================="
echo "AutoKey macOS Standalone Executable Builder"
echo "============================================="

# Check if python3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: python3 is not installed or not in your PATH."
    exit 1
fi

# Install PyInstaller
echo "[1/3] Checking and installing PyInstaller..."
python3 -m pip install --upgrade pip
python3 -m pip install pyinstaller

# Build the executable
echo "[2/3] Compiling standalone app using PyInstaller..."
# --add-data "web:web" bundles the static assets
# --noconsole hides the default terminal window
python3 -m PyInstaller --onefile --noconsole --add-data "web:web" --name "AutoKey" --noconfirm app.py

echo "[3/3] Build completed successfully!"
echo "👉 The executable is located at: dist/AutoKey"
echo "👉 Double-click it to start the background process and launch the browser control page!"
echo "============================================="
