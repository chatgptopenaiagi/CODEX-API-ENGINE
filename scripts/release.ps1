$ErrorActionPreference = 'Stop'
& "$PSScriptRoot/test.ps1"
& "$PSScriptRoot/build.ps1" -Executable
Get-ChildItem (Join-Path (Split-Path $PSScriptRoot -Parent) 'dist') -File |
    Where-Object { $_.Extension -in '.whl','.gz','.exe' } |
    Get-FileHash -Algorithm SHA256 |
    Select-Object @{Name='File';Expression={Split-Path $_.Path -Leaf}},Hash |
    ConvertTo-Json | Set-Content (Join-Path (Split-Path $PSScriptRoot -Parent) 'dist/SHA256SUMS.json')
