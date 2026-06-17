#requires -Version 5.1

# Installer for Windows PowerShell
# Creates venv, installs requirements, creates data dirs.

$ErrorActionPreference = 'Stop'

$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectDir

function Log([string]$msg) { Write-Host "[INFO] $msg" }
function Warn([string]$msg) { Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Err([string]$msg) { Write-Host "[ERROR] $msg" -ForegroundColor Red; throw $msg }

# Validate python
if (-not (Get-Command python -ErrorAction SilentlyContinue) -and -not (Get-Command py -ErrorAction SilentlyContinue)) {
  Err "Python not found. Install Python 3.11+ and ensure it is available in PATH."
}

# Create venv if missing
if (-not (Test-Path -Path "venv")) {
  Log "Creating virtual environment (venv)..."
  if (Get-Command py -ErrorAction SilentlyContinue) {
    py -3.11 -m venv venv
  } else {
    python -m venv venv
  }
}

$venvPython = Join-Path $projectDir "venv\Scripts\python.exe"
$venvPip = Join-Path $projectDir "venv\Scripts\pip.exe"

if (-not (Test-Path -Path $venvPython)) {
  Err "venv python.exe not found at $venvPython"
}

Log "Upgrading pip..."
& $venvPip install -U pip setuptools wheel

Log "Installing Python dependencies..."
& $venvPip install -r requirements.txt

Log "Creating runtime directories..."
New-Item -ItemType Directory -Force -Path "data\logs" | Out-Null
New-Item -ItemType Directory -Force -Path "data\exports" | Out-Null
New-Item -ItemType Directory -Force -Path "data\clean_ips" | Out-Null

if (-not (Test-Path -Path ".env")) {
  Warn ".env not found. Creating from .env.example (if exists)..."
  if (Test-Path -Path ".env.example") {
    Copy-Item ".env.example" ".env"
  } else {
    New-Item -ItemType File -Path ".env" | Out-Null
  }
  Warn "Edit .env before starting if needed."
}

Log "Done. To start:"
Log "  & `"$venvPython`" main.py"

