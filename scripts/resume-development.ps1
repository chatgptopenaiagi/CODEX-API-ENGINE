# Read-only checkpoint inspection. Does not fetch, initialize tools or run CAE.
[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$project = Get-Content -LiteralPath (Join-Path $root 'pyproject.toml') -Raw
$version = [regex]::Match($project, '(?m)^version\s*=\s*"([^"]+)"').Groups[1].Value
if (-not $version) { throw 'Cannot read project version' }
Write-Output "CAE version: $version"
if (Get-Command git -ErrorAction SilentlyContinue) {
    Write-Output 'Branch:'
    git --no-optional-locks -C $root branch --show-current
    Write-Output 'Latest commit:'
    git --no-optional-locks -C $root log -1 --format='%H %s'
    Write-Output 'Working tree:'
    git --no-optional-locks -C $root status --short
    Write-Output 'Remotes (embedded credentials redacted):'
    git --no-optional-locks -C $root remote -v | ForEach-Object {
        $_ -replace '(https?://)[^/\s]+@', '$1[redacted]@' -replace '\?[^\s]+', '?[redacted]'
    }
} else { Write-Warning 'Git is not available' }
Write-Output 'Tool availability (no runtime initialization):'
foreach ($tool in @('git', 'gh', 'pwsh', 'py', 'dotnet', 'node', 'clang++')) {
    Write-Output ('{0}: {1}' -f $tool, [bool](Get-Command $tool -ErrorAction SilentlyContinue))
}
Write-Output ('Repository Python: {0}' -f (Test-Path -LiteralPath (Join-Path $root '.venv/Scripts/python.exe')))
Write-Output 'Check compiler/SDK versions against docs/continuity/ENVIRONMENT_STATE.md.'
$checkpoint = Join-Path $root 'docs/continuity'
$next = Join-Path $checkpoint 'NEXT_SESSION.md'
Write-Output "Checkpoint: $checkpoint"
if (Test-Path -LiteralPath $next) {
    Get-Content -LiteralPath $next | Where-Object { $_ -match '^- Next milestone:' }
    Write-Output "Read next: $next"
} else { Write-Warning 'Continuation checkpoint is missing' }
