# DorkHub installer for Windows (PowerShell).
# Sets up the Python backend, builds the frontend, creates .env, and asks for the
# login password during install.
#
# If PowerShell blocks this script, run once:
#   Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
# Then:  .\install.ps1

$ErrorActionPreference = "Stop"

$Root     = Split-Path -Parent $MyInvocation.MyCommand.Path
$Backend  = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"
$EnvFile  = Join-Path $Root ".env"

function Say  ($m) { Write-Host "==> $m" -ForegroundColor Cyan }
function Warn ($m) { Write-Host "!   $m" -ForegroundColor Yellow }
function Die  ($m) { Write-Host "xx  $m" -ForegroundColor Red; exit 1 }

# ---------- prerequisites ----------
$py = $null
foreach ($c in @("python", "py")) {
  if (Get-Command $c -ErrorAction SilentlyContinue) { $py = $c; break }
}
if (-not $py) { Die "Python 3 not found. Install Python 3.12+ and retry." }
Say "Using Python command: $py"

$haveNode = [bool](Get-Command npm -ErrorAction SilentlyContinue)
if (-not $haveNode) { Warn "Node.js/npm not found. The web UI build will be skipped." }

# ---------- backend venv + deps ----------
Say "Creating virtual environment and installing backend dependencies..."
Set-Location $Backend
& $py -m venv .venv
$venvPy = Join-Path $Backend ".venv\Scripts\python.exe"
& $venvPy -m pip install --quiet --upgrade pip
& $venvPy -m pip install --quiet -r requirements.txt
Say "Backend dependencies installed."

# ---------- password prompt ----------
$pw = $null
while ($true) {
  $s1 = Read-Host "Set DorkHub login password" -AsSecureString
  $s2 = Read-Host "Confirm password" -AsSecureString
  $p1 = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
          [Runtime.InteropServices.Marshal]::SecureStringToBSTR($s1))
  $p2 = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
          [Runtime.InteropServices.Marshal]::SecureStringToBSTR($s2))
  if (-not $p1) { Warn "Password cannot be empty." ; continue }
  if ($p1 -ne $p2) { Warn "Passwords do not match, try again." ; continue }
  $pw = $p1; break
}

Say "Hashing password..."
$hash   = ($pw | & $venvPy -m app.cli hash-password)
$secret = (& $venvPy -m app.cli gen-secret)
$pw = $null; $p1 = $null; $p2 = $null

# ---------- write .env ----------
Set-Location $Root
$writeEnv = "true"
if (Test-Path $EnvFile) {
  $ans = Read-Host ".env already exists. Overwrite password + secret in it? [y/N]"
  if ($ans -match '^[yY]') { $writeEnv = "update" } else { $writeEnv = "false"; Warn "Keeping existing .env unchanged." }
}

function Set-EnvLine($lines, $key, $value) {
  $found = $false
  $out = foreach ($ln in $lines) {
    if ($ln.StartsWith("$key=")) { $found = $true; "$key=$value" } else { $ln }
  }
  if (-not $found) { $out += "$key=$value" }
  return $out
}

if ($writeEnv -eq "true") {
  Copy-Item (Join-Path $Root ".env.example") $EnvFile -Force
}
if ($writeEnv -ne "false") {
  $lines = Get-Content $EnvFile
  $lines = Set-EnvLine $lines "DORKHUB_AUTH_PASSWORD_HASH" $hash
  $lines = Set-EnvLine $lines "DORKHUB_SECRET_KEY" $secret
  Set-Content -Path $EnvFile -Value $lines -Encoding UTF8
  Say "Wrote password + secret to $EnvFile"
}
$hash = $null; $secret = $null

# ---------- db + dorks ----------
Set-Location $Backend
Say "Initializing database and importing the dork library..."
& $venvPy -m app.cli initdb
& $venvPy -m app.cli import-dorks

# ---------- frontend build ----------
if ($haveNode) {
  Say "Installing and building the web UI..."
  Set-Location $Frontend
  npm install --silent
  npm run build --silent
  Say "Web UI built into backend/static."
} else {
  Warn "npm not available; skipped UI build. Install Node.js 20+, then: cd frontend; npm install; npm run build"
}

Write-Host ""
Say "Installation complete."
Write-Host @"

To start DorkHub:

  cd backend
  .venv\Scripts\Activate.ps1
  uvicorn app.main:app --host 0.0.0.0 --port 8000

Then open http://localhost:8000 and sign in with your password.

Before running real searches, add a provider key to .env
(DORKHUB_SERPER_API_KEY or DataForSEO credentials).
"@
