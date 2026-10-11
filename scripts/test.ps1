$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$env:TEMP = Join-Path (Get-Location) '.tmp'
$env:TMP = $env:TEMP
./.venv/Scripts/python.exe -m ruff check src tests scripts examples gui
if ($LASTEXITCODE -ne 0) { throw 'Lint failed' }
./.venv/Scripts/python.exe -m mypy
if ($LASTEXITCODE -ne 0) { throw 'Type checks failed' }
./.venv/Scripts/python.exe -m pytest --basetemp .tmp/pytest --cov=cae --cov-report=term-missing --cov-fail-under=80
if ($LASTEXITCODE -ne 0) { throw 'Tests failed' }
