# Starts the FastAPI backend. Creates the venv and installs deps on first run.
param(
    [int]$Port = 8000
)
$ErrorActionPreference = 'Stop'
Set-Location "$PSScriptRoot/../backend"

if (-not (Test-Path .venv)) {
    Write-Host 'Creating virtual environment and installing dependencies...'
    python -m venv .venv
    .\.venv\Scripts\python.exe -m pip install --upgrade pip
    .\.venv\Scripts\python.exe -m pip install -r requirements.txt
}

.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port $Port
