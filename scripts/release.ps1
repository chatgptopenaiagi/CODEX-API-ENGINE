$ErrorActionPreference = 'Stop'
& "$PSScriptRoot/test.ps1"
& "$PSScriptRoot/build.ps1" -Executable
./.venv/Scripts/python.exe scripts/checksums.py
if ($LASTEXITCODE -ne 0) { throw 'Checksum generation failed' }
./.venv/Scripts/python.exe scripts/check_release.py
if ($LASTEXITCODE -ne 0) { throw 'Release integrity failed' }
& "$PSScriptRoot/test_broker_apps.ps1"
