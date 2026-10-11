param([switch]$Executable)
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
New-Item -ItemType Directory -Force .tmp,.cache | Out-Null
$env:TEMP = Join-Path (Get-Location) '.tmp'
$env:TMP = $env:TEMP
$env:PYINSTALLER_CONFIG_DIR = Join-Path (Get-Location) '.cache/pyinstaller'
./.venv/Scripts/python.exe scripts/validate_version.py
if ($LASTEXITCODE -ne 0) { throw 'Version validation failed' }
$buildVersion = & ./.venv/Scripts/python.exe -c "import tomllib; print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])"
$artifactDirectory = Join-Path 'dist' $buildVersion
./.venv/Scripts/python.exe -m build --no-isolation --outdir $artifactDirectory
if ($LASTEXITCODE -ne 0) { throw 'Wheel/source build failed' }
./.venv/Scripts/python.exe scripts/check_artifacts.py --directory $artifactDirectory
if ($LASTEXITCODE -ne 0) { throw 'Artifact verification failed' }
if ($Executable) {
    ./.venv/Scripts/python.exe -m PyInstaller --noconfirm --onefile --windowed --name CAE-Control-Center --paths src --distpath $artifactDirectory --workpath build/pyinstaller-access --specpath build gui/control_launcher.py
    if ($LASTEXITCODE -ne 0) { throw 'Executable build failed' }
    ./.venv/Scripts/python.exe scripts/check_artifacts.py --directory $artifactDirectory
    if ($LASTEXITCODE -ne 0) { throw 'Artifact verification failed' }
    $executablePath = (Resolve-Path -LiteralPath (Join-Path $artifactDirectory 'CAE-Control-Center.exe')).Path
    $smokeProcess = Start-Process -FilePath $executablePath -ArgumentList '--self-test' -WindowStyle Hidden -PassThru
    if (-not $smokeProcess.WaitForExit(30000)) {
        Stop-Process -Id $smokeProcess.Id
        throw 'Executable smoke test timed out'
    }
    if ($smokeProcess.ExitCode -ne 0) { throw 'Executable smoke test failed' }
    $additionalTargets = @(
        @{ Name = 'CAE-Broker'; Script = 'gui/broker_launcher.py'; Mode = '--windowed' },
        @{ Name = 'CAE-Console-Client'; Script = 'examples/broker_console.py'; Mode = '--console' },
        @{ Name = 'CAE-Desktop-Client'; Script = 'examples/broker_desktop.py'; Mode = '--windowed' }
    )
    foreach ($target in $additionalTargets) {
        ./.venv/Scripts/python.exe -m PyInstaller --noconfirm --onefile $target.Mode --name $target.Name --paths src --distpath $artifactDirectory --workpath (Join-Path 'build' $target.Name) --specpath build $target.Script
        if ($LASTEXITCODE -ne 0) { throw 'Additional executable build failed' }
        $targetPath = (Resolve-Path -LiteralPath (Join-Path $artifactDirectory ($target.Name + '.exe'))).Path
        $targetProcess = Start-Process -FilePath $targetPath -ArgumentList '--self-test' -WindowStyle Hidden -PassThru
        if (-not $targetProcess.WaitForExit(30000)) {
            Stop-Process -Id $targetProcess.Id
            throw 'Additional executable smoke timed out'
        }
        if ($targetProcess.ExitCode -ne 0) { throw 'Additional executable smoke failed' }
    }
    ./.venv/Scripts/python.exe scripts/check_artifacts.py --directory $artifactDirectory
    if ($LASTEXITCODE -ne 0) { throw 'Final artifact verification failed' }
}
