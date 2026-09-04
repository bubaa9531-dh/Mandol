# =============================================================================
# Mandol-AML local one-shot deploy + connectivity test (Windows PowerShell)
# Usage:   powershell -ExecutionPolicy Bypass -File aml\scripts\deploy_local.ps1
# Env:     REPO_URL / WORK_DIR / BASE_URL / SKIP_INSTALL=1 / SKIP_TESTS=1
# =============================================================================
$ErrorActionPreference = "Stop"
$repoUrl = if ($env:REPO_URL) { $env:REPO_URL } else { "https://github.com/bubaa9531-dh/Mandol.git" }
$workDir = if ($env:WORK_DIR) { $env:WORK_DIR } else { Join-Path (Get-Location) "Mandol-local" }
$skipInstall = ($env:SKIP_INSTALL -eq "1")
$skipTests = ($env:SKIP_TESTS -eq "1")

function Say($step, $msg) { Write-Host ""; Write-Host "[$step] $msg" -ForegroundColor Cyan }

Say "1/5" "Fetch code -> $workDir"
if (-not (Test-Path (Join-Path $workDir ".git"))) {
  git clone $repoUrl $workDir
} else {
  Push-Location $workDir
  try { git fetch --all --prune; git checkout main; git pull --ff-only origin main } finally { Pop-Location }
}

Say "2/5" "Check environment"
python --version
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
  Write-Host "uv not found; installing via pip ..."
  python -m pip install uv
}

Say "3/5" "Install dependencies (uv sync --frozen --no-dev)"
if (-not $skipInstall) {
  Push-Location $workDir
  try { uv sync --frozen --no-dev } finally { Pop-Location }
}

if (-not $skipTests) {
  Say "3b/5" "Run unit tests"
  Push-Location $workDir
  try { uv run pytest tests/ -q } finally { Pop-Location }
}

Say "4/5" "Prepare .env (copy template if missing)"
Push-Location $workDir
try {
  if (-not (Test-Path ".env")) { Copy-Item "aml.env.example" ".env"; Write-Host "Created .env - edit if needed" }
} finally { Pop-Location }

Say "5/5" "Run local end-to-end connectivity test"
Push-Location $workDir
try { uv run python aml/scripts/run_local_e2e.py } finally { Pop-Location }

Write-Host ""
Write-Host "==============================================================" -ForegroundColor Green
Write-Host " Local connectivity test PASSED: Add -> Search chain works."
Write-Host " Next: set Memory System Key -> platform Smoke -> Full evaluation."
Write-Host "==============================================================" -ForegroundColor Green
