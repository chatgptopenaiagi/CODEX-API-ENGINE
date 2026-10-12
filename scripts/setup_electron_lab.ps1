$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$env:TEMP = Join-Path (Get-Location) '.tmp'
$env:TMP = $env:TEMP
$env:npm_config_cache = Join-Path (Get-Location) '.cache/npm'
$env:electron_config_cache = Join-Path (Get-Location) '.cache/electron'
npm.cmd install --prefix .tmp/electron-lab --ignore-scripts --no-audit --no-fund electron@44.7.0
if ($LASTEXITCODE) { throw 'Electron package installation failed' }
# This explicit installer checks its published checksums and uses the repository cache.
node .tmp/electron-lab/node_modules/electron/install.js
if ($LASTEXITCODE) { throw 'Electron runtime installation failed' }
