# Run the full pipeline: extract PDFs -> merge -> generate LaTeX -> compile PDF
$ErrorActionPreference = "Stop"

$env:PATH += ";$env:USERPROFILE\.local\bin;$env:LOCALAPPDATA\Programs\MiKTeX\miktex\bin\x64"

New-Item -ItemType Directory -Path output -Force | Out-Null

$stateFile = "output/.pipeline_hashes"
$state = @{}

function Get-SourceHash {
    param([Parameter(Mandatory = $true)][string]$Path)

    return (Get-FileHash -Algorithm SHA256 -Path $Path).Hash.ToLowerInvariant()
}

function Test-AllOutputsExist {
    param([string[]]$Paths)

    foreach ($path in $Paths) {
        if (-not (Test-Path $path)) {
            return $false
        }
    }

    return $true
}

function Should-RunStep {
    param(
        [string]$StepName,
        [string]$CurrentHash,
        [string[]]$ExpectedOutputs,
        [bool]$UpstreamChanged = $false
    )

    if ($UpstreamChanged) {
        return $true
    }

    if (-not (Test-AllOutputsExist -Paths $ExpectedOutputs)) {
        return $true
    }

    if (-not $state.ContainsKey($StepName)) {
        return $true
    }

    return $state[$StepName] -ne $CurrentHash
}

if (Test-Path $stateFile) {
    foreach ($line in Get-Content $stateFile) {
        if ($line -match '^([^=]+)=(.*)$') {
            $state[$matches[1]] = $matches[2]
        }
    }
}

Write-Host "=== Step 1: Extract 2024 synopsis ===" -ForegroundColor Cyan
$extract2024Hash = Get-SourceHash "src/extract_synopsis.py"
$extract2024Ran = Should-RunStep -StepName "extract" -CurrentHash $extract2024Hash -ExpectedOutputs @("output/synopsis_2024_raw.json")
if ($extract2024Ran) {
    uv run python src/extract_synopsis.py `
        "input/2024-09_Referentenentwurf_Synopse.pdf" `
        "output/synopsis_2024_raw.json"
    $state["extract"] = $extract2024Hash
}
else {
    Write-Host "Skipping extract 2024 (no relevant changes detected)." -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "=== Step 2: Extract 2026 synopsis ===" -ForegroundColor Cyan
$extract2026Hash = Get-SourceHash "src/extract_synopsis.py"
$extract2026Ran = Should-RunStep -StepName "extract" -CurrentHash $extract2026Hash -ExpectedOutputs @("output/synopsis_2026_raw.json")
if ($extract2026Ran) {
    uv run python src/extract_synopsis.py `
        "input/2026-03_Referentenentwurf_Synopse.pdf" `
        "output/synopsis_2026_raw.json"
    $state["extract"] = $extract2026Hash
}
else {
    Write-Host "Skipping extract 2026 (no relevant changes detected)." -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "=== Step 3: Align and merge synopses ===" -ForegroundColor Cyan
$alignMergeHash = Get-SourceHash "src/align_and_merge.py"
$extractRan = $extract2024Ran -or $extract2026Ran
$alignMergeRan = Should-RunStep -StepName "align_merge" -CurrentHash $alignMergeHash -ExpectedOutputs @("output/synopsis_merged.json") -UpstreamChanged:$extractRan
if ($alignMergeRan) {
    uv run python src/align_and_merge.py `
        output/synopsis_2024_raw.json `
        output/synopsis_2026_raw.json `
        output/synopsis_merged.json
    $state["align_merge"] = $alignMergeHash
}
else {
    Write-Host "Skipping align/merge (no relevant changes detected)." -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "=== Step 4: Generate LaTeX ===" -ForegroundColor Cyan
$generateLatexHash = Get-SourceHash "src/generate_latex.py"
$generateRan = Should-RunStep -StepName "generate_latex" -CurrentHash $generateLatexHash -ExpectedOutputs @("output/synopsis_combined.tex") -UpstreamChanged:$alignMergeRan
if ($generateRan) {
    uv run python src/generate_latex.py `
        output/synopsis_merged.json `
        output/synopsis_combined.tex
    $state["generate_latex"] = $generateLatexHash
}
else {
    Write-Host "Skipping LaTeX generation (no relevant changes detected)." -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "=== Step 5: Compile PDF ===" -ForegroundColor Cyan
$compileRan = $false
if (-not (Test-Path "output/synopsis_combined.pdf")) {
    $compileRan = $true
}
elseif ($generateRan) {
    $compileRan = $true
}
else {
    $texFile = Get-Item "output/synopsis_combined.tex"
    $pdfFile = Get-Item "output/synopsis_combined.pdf"
    $compileRan = $texFile.LastWriteTimeUtc -gt $pdfFile.LastWriteTimeUtc
}

if ($compileRan) {
    Push-Location output
    xelatex -interaction=nonstopmode synopsis_combined.tex
    Pop-Location
}
else {
    Write-Host "Skipping PDF compile (up to date)." -ForegroundColor DarkGray
}

$serializedState = $state.GetEnumerator() |
Sort-Object Name |
ForEach-Object { "$($_.Key)=$($_.Value)" }
Set-Content -Path $stateFile -Value $serializedState -Encoding UTF8

Write-Host ""
Write-Host "=== Done ===" -ForegroundColor Green
Write-Host "Output: output/synopsis_combined.pdf"
