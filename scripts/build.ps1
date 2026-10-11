param([switch]$Executable)
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
New-Item -ItemType Directory -Force .tmp,.cache | Out-Null
$env:TEMP = Join-Path (Get-Location) '.tmp'
$env:TMP = $env:TEMP
$env:PYINSTALLER_CONFIG_DIR = Join-Path (Get-Location) '.cache/pyinstaller'
./.venv/Scripts/python.exe scripts/validate_version.py
if ($LASTEXITCODE -ne 0) { throw 'Version validation failed' }
./.venv/Scripts/python.exe -m build --no-isolation
if ($LASTEXITCODE -ne 0) { throw 'Wheel/source build failed' }
./.venv/Scripts/python.exe scripts/check_artifacts.py
if ($LASTEXITCODE -ne 0) { throw 'Artifact verification failed' }
if ($Executable) {
    ./.venv/Scripts/python.exe -m PyInstaller --noconfirm --onefile --windowed --name CAE-Test-Console --paths src --distpath dist --workpath build/pyinstaller --specpath build gui/launcher.py
    if ($LASTEXITCODE -ne 0) { throw 'Executable build failed' }
    ./.venv/Scripts/python.exe scripts/check_artifacts.py
    if ($LASTEXITCODE -ne 0) { throw 'Artifact verification failed' }
    $executablePath = (Resolve-Path -LiteralPath 'dist/CAE-Test-Console.exe').Path
    $smokeProcess = Start-Process -FilePath $executablePath -ArgumentList '--self-test' -WindowStyle Hidden -PassThru
    if (-not $smokeProcess.WaitForExit(30000)) {
        Stop-Process -Id $smokeProcess.Id
        throw 'Executable smoke test timed out'
    }
    if ($smokeProcess.ExitCode -ne 0) { throw 'Executable smoke test failed' }
}
