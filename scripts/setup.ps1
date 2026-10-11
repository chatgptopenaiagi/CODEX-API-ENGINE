$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
New-Item -ItemType Directory -Force .tmp | Out-Null
$env:TEMP = Join-Path (Get-Location) '.tmp'
$env:TMP = $env:TEMP
if (-not (Test-Path .venv/Scripts/python.exe)) {
    py -3.14 -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.14 environment creation failed' }
}
./.venv/Scripts/python.exe -m pip --isolated install --disable-pip-version-check --no-cache-dir -e '.[dev]'
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed' }
