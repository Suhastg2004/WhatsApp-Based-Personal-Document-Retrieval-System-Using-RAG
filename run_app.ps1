param(
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$venvPython = Join-Path $PSScriptRoot "major_project\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "Virtual environment not found at major_project\Scripts\python.exe" -ForegroundColor Red
    Write-Host "Create it first: python -m venv major_project"
    exit 1
}

if (-not (Test-Path (Join-Path $PSScriptRoot ".env"))) {
    if (Test-Path (Join-Path $PSScriptRoot ".env.example")) {
        Copy-Item (Join-Path $PSScriptRoot ".env.example") (Join-Path $PSScriptRoot ".env")
        Write-Host "Created .env from .env.example"
    } else {
        Write-Host ".env not found, and .env.example is missing." -ForegroundColor Red
        exit 1
    }
}

if (-not $SkipInstall) {
    Write-Host "Installing/updating dependencies..."
    & $venvPython -m pip install -r requirements.txt
}

try {
    $null = tesseract --version
} catch {
    Write-Host "Warning: Tesseract not found. OCR for images/scanned PDFs may fail." -ForegroundColor Yellow
}

Write-Host "Starting API at http://localhost:8000"
Write-Host "Swagger docs: http://localhost:8000/docs"
& $venvPython -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
