# First-time setup for NSE Intraday Scanner (Windows)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

Write-Host "Setting up NSE Intraday Scanner..." -ForegroundColor Cyan

# Backend venv
Push-Location "$Root\backend"
if (-not (Test-Path ".venv")) {
    python -m venv .venv
}
& .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Pop-Location

# Frontend
Push-Location "$Root\frontend"
npm install
Pop-Location

# Directories
New-Item -ItemType Directory -Force -Path "$Root\data" | Out-Null
New-Item -ItemType Directory -Force -Path "$Root\logs" | Out-Null

# Env file
if (-not (Test-Path "$Root\.env")) {
    Copy-Item "$Root\.env.example" "$Root\.env"
    Write-Host "Created .env from .env.example" -ForegroundColor Yellow
}

Write-Host "Setup complete. Run scripts\start-all.ps1 to launch." -ForegroundColor Green
