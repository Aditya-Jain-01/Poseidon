$ErrorActionPreference = 'Stop'

Set-Location -LiteralPath $PSScriptRoot

if (Test-Path -LiteralPath '.venv\Scripts\python.exe') {
    $pythonExe = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
} elseif (Test-Path -LiteralPath 'venv\Scripts\python.exe') {
    $pythonExe = Join-Path $PSScriptRoot 'venv\Scripts\python.exe'
} else {
    Write-Host 'Creating Python environment in .venv...'
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the Python environment.' }
    $pythonExe = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
}

Write-Host 'Installing Python dependencies...'
& $pythonExe -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Python dependency installation failed.' }

Write-Host 'Preparing the local embedding model...'
& $pythonExe backend/scripts/prepare_embeddings.py --download
if ($LASTEXITCODE -ne 0) { throw 'Embedding model setup failed.' }

Write-Host 'Installing frontend dependencies...'
npm.cmd ci --prefix frontend
if ($LASTEXITCODE -ne 0) { throw 'Frontend dependency installation failed.' }

if (-not (Test-Path -LiteralPath '.env')) {
    Copy-Item -LiteralPath '.env.example' -Destination '.env'
    Write-Host 'Created .env from .env.example. Configure your answer model before starting Poseidon.'
}

Write-Host 'Setup complete. The embedding model is ready for offline use.'
Write-Host "Backend Python: $pythonExe"
