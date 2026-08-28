# Starts the Vite frontend dev server. Installs node modules on first run.
param(
    [switch]$Install
)
$ErrorActionPreference = 'Stop'
Set-Location "$PSScriptRoot/../frontend"

if ($Install -or -not (Test-Path node_modules)) {
    Write-Host 'Installing frontend dependencies...'
    npm install
}

npm run dev
