$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$env:TEMP = Join-Path (Get-Location) '.tmp'
$env:TMP = $env:TEMP
$version = & ./.venv/Scripts/python.exe -c "import tomllib; print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])"
./.venv/Scripts/python.exe -m venv .tmp/broker-smoke-wheel
if ($LASTEXITCODE -ne 0) { throw 'Isolated environment creation failed' }
./.tmp/broker-smoke-wheel/Scripts/python.exe -m pip install --no-index --no-deps --force-reinstall "dist/$version/codex_api_engine-$version-py3-none-any.whl"
if ($LASTEXITCODE -ne 0) { throw 'Isolated wheel installation failed' }
$runDirectory = '.tmp/broker-smoke-' + [guid]::NewGuid().ToString('N')
./.tmp/broker-smoke-wheel/Scripts/python.exe -I scripts/validate_broker_apps.py --artifacts "dist/$version" --work $runDirectory
if ($LASTEXITCODE -ne 0) { throw 'Independent broker/client validation failed' }
