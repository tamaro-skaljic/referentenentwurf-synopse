#!/bin/bash
# Setup script for the synopsis comparison project.
# Installs uv, Python, dependencies, and MiKTeX.
set -e

echo "=== Setting up synopsis comparison tools ==="

# 1. Install uv if not present
if ! command -v uv &> /dev/null; then
    echo "Installing uv..."
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    export PATH="$PATH:$HOME/.local/bin"
fi
echo "uv: $(uv --version)"

# 2. Install Python dependencies
echo "Installing Python dependencies..."
uv sync

# 3. Install MiKTeX if xelatex not found
if ! command -v xelatex &> /dev/null; then
    MIKTEX_PATH="$HOME/AppData/Local/Programs/MiKTeX/miktex/bin/x64"
    if [ -f "$MIKTEX_PATH/xelatex.exe" ]; then
        export PATH="$PATH:$MIKTEX_PATH"
    else
        echo "Installing MiKTeX..."
        winget install MiKTeX.MiKTeX --accept-source-agreements --accept-package-agreements
        export PATH="$PATH:$MIKTEX_PATH"
    fi
fi
echo "xelatex: $(xelatex --version 2>&1 | head -1)"

echo ""
echo "=== Setup complete ==="
echo "Run ./run.sh to generate the combined synopsis PDF."
