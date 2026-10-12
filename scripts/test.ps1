$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$env:TEMP = Join-Path (Get-Location) '.tmp'
$env:TMP = $env:TEMP
$buildVersion = & ./.venv/Scripts/python.exe -c "import cae; print(cae.__version__)"
if (-not (Test-Path -LiteralPath "dist/$buildVersion/CAE-Broker.exe") -or
    -not (Test-Path -LiteralPath 'dist/0.4.0-clients/CAE-Cpp-Client.exe')) {
    throw 'Full validation requires scripts/build.ps1 -Executable and scripts/build_clients.ps1 first. Python-only tests can be run with pytest.'
}
./.venv/Scripts/python.exe -m ruff check src tests scripts examples gui clients/python/src integration-lab/python-client
if ($LASTEXITCODE -ne 0) { throw 'Lint failed' }
./.venv/Scripts/python.exe -m mypy
if ($LASTEXITCODE -ne 0) { throw 'Type checks failed' }
./.venv/Scripts/python.exe -m mypy clients/python/src/cae_client
if ($LASTEXITCODE -ne 0) { throw 'Client type checks failed' }
./.venv/Scripts/python.exe -m pytest --basetemp .tmp/pytest --cov=cae --cov=cae_client --cov-report=term-missing --cov-report=json:.tmp/coverage.json --cov-fail-under=90
if ($LASTEXITCODE -ne 0) { throw 'Tests failed' }
./.venv/Scripts/python.exe scripts/check_coverage.py
if ($LASTEXITCODE -ne 0) { throw 'Security coverage gate failed' }
