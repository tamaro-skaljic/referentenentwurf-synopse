# Run the full pipeline: extract PDFs -> merge -> generate LaTeX -> compile PDF
$ErrorActionPreference = "Stop"

$env:PATH += ";$env:USERPROFILE\.local\bin;$env:LOCALAPPDATA\Programs\MiKTeX\miktex\bin\x64"

Write-Host "Cleaning output directory..." -ForegroundColor Yellow
if (Test-Path output) { Remove-Item output\* -Recurse -Force -ErrorAction SilentlyContinue }
New-Item -ItemType Directory -Path output -Force | Out-Null

Write-Host "=== Step 1: Extract 2024 synopsis ===" -ForegroundColor Cyan
uv run python src/extract_synopsis.py `
    "input/2024-09_Referentenentwurf_Synopse.pdf" `
    "output/synopsis_2024.json"

Write-Host ""
Write-Host "=== Step 2: Extract 2026 synopsis ===" -ForegroundColor Cyan
uv run python src/extract_synopsis.py `
    "input/2026-03_Referentenentwurf_Synopse.pdf" `
    "output/synopsis_2026.json"

Write-Host ""
Write-Host "=== Step 3: Merge synopses ===" -ForegroundColor Cyan
uv run python src/merge_synopses.py `
    output/synopsis_2024.json `
    output/synopsis_2026.json `
    output/synopsis_merged.json

Write-Host ""
Write-Host "=== Step 4: Generate LaTeX ===" -ForegroundColor Cyan
uv run python src/generate_latex.py `
    output/synopsis_merged.json `
    output/synopsis_combined.tex

Write-Host ""
Write-Host "=== Step 5: Compile PDF ===" -ForegroundColor Cyan
Push-Location output
xelatex -interaction=nonstopmode synopsis_combined.tex
Pop-Location

Write-Host ""
Write-Host "=== Done ===" -ForegroundColor Green
Write-Host "Output: output/synopsis_combined.pdf"
