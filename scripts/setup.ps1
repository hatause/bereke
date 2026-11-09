$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
function Check-Exit { if ($LASTEXITCODE -ne 0) { throw "Command failed: $LASTEXITCODE" } }
if (!(Test-Path '.venv/Scripts/python.exe')) { py -3 -m venv .venv; Check-Exit }
& ./.venv/Scripts/python.exe -c "import sys; assert sys.version_info >= (3,12), 'Python 3.12+ required'"; Check-Exit
& ./.venv/Scripts/python.exe -m pip install -r backend/requirements-dev.txt; Check-Exit
Push-Location backend
try {
  & ../.venv/Scripts/python.exe -m alembic upgrade head; Check-Exit
  & ../.venv/Scripts/python.exe -m app.seed; Check-Exit
} finally { Pop-Location }
Push-Location frontend
try { npm ci; Check-Exit } finally { Pop-Location }
Write-Output 'Ready. Run scripts/backend.ps1 and scripts/frontend.ps1 in separate terminals.'
