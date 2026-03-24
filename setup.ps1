# Setup script for the synopsis comparison project.
# Installs uv, Python, dependencies, and MiKTeX.
$ErrorActionPreference = "Stop"

Write-Host "=== Setting up synopsis comparison tools ===" -ForegroundColor Cyan

# 1. Install uv if not present
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "Installing uv..."
    irm https://astral.sh/uv/install.ps1 | iex
    $env:PATH += ";$env:USERPROFILE\.local\bin"
}
Write-Host "uv: $(uv --version)"

# 2. Install Python dependencies
Write-Host "Installing Python dependencies..."
uv sync

# 3. Install MiKTeX if xelatex not found
$miktexPath = "$env:LOCALAPPDATA\Programs\MiKTeX\miktex\bin\x64"
if (-not (Get-Command xelatex -ErrorAction SilentlyContinue)) {
    if (Test-Path "$miktexPath\xelatex.exe") {
        $env:PATH += ";$miktexPath"
    } else {
        Write-Host "Installing MiKTeX..."
        winget install MiKTeX.MiKTeX --accept-source-agreements --accept-package-agreements
        $env:PATH += ";$miktexPath"
    }
}
Write-Host "xelatex: $((xelatex --version 2>&1) | Select-Object -First 1)"

Write-Host ""
Write-Host "=== Setup complete ===" -ForegroundColor Green
Write-Host "Run .\run.ps1 to generate the combined synopsis PDF."
