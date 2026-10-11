param([string]$OutputDirectory = 'dist/0.4.0-clients')
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$root = (Get-Location).Path
$out = [IO.Path]::GetFullPath((Join-Path $root $OutputDirectory))
if (-not $out.StartsWith($root + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Output must be repository-local' }
$env:TEMP = Join-Path $root '.tmp'
$env:TMP = $env:TEMP
$env:DOTNET_CLI_HOME = Join-Path $root '.cache/dotnet'
$env:DOTNET_SKIP_FIRST_TIME_EXPERIENCE = '1'
$env:DOTNET_CLI_TELEMETRY_OPTOUT = '1'
$env:DOTNET_GENERATE_ASPNET_CERTIFICATE = 'false'
$env:DOTNET_ADD_GLOBAL_TOOLS_TO_PATH = 'false'
$env:NUGET_PACKAGES = Join-Path $root '.cache/nuget'
$env:npm_config_cache = Join-Path $root '.cache/npm'
$deps = Join-Path $root '.cache/client-deps'
New-Item -ItemType Directory -Force $out,$deps,(Join-Path $deps 'include/nlohmann') | Out-Null
function Fetch-Verified($Name, $Url, $Hash) {
    $target = Join-Path $deps $Name
    if (-not (Test-Path -LiteralPath $target)) { Invoke-WebRequest $Url -OutFile $target }
    if ((Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash -ne $Hash) { throw "Dependency hash mismatch: $Name" }
}
Fetch-Verified 'json.hpp' 'https://raw.githubusercontent.com/nlohmann/json/v3.12.0/single_include/nlohmann/json.hpp' 'AAF127C04CB31C406E5B04A63F1AE89369FCCDE6D8FA7CDDA1ED4F32DFC5DE63'
Fetch-Verified 'JSON-LICENSE' 'https://raw.githubusercontent.com/nlohmann/json/v3.12.0/LICENSE.MIT' '46A65CFFD1EA955132D95A8DD921640714A8D6B537D2E4E482D31145AE95B603'
Fetch-Verified 'node-headers.tar.gz' 'https://nodejs.org/dist/v26.8.1/node-v26.8.1-headers.tar.gz' 'E4F54DECDBF7EADB121C39C050F04F5430A7AF1D035BB8DED501171637FE72DE'
Fetch-Verified 'node.lib' 'https://nodejs.org/dist/v26.8.1/win-x64/node.lib' '5432DCEEAC196EF89EC001939CC3801CFA131036A05F5FABF5E07B6C5A0895A4'
Copy-Item -LiteralPath (Join-Path $deps 'json.hpp') -Destination (Join-Path $deps 'include/nlohmann/json.hpp')
tar -xzf (Join-Path $deps 'node-headers.tar.gz') -C $deps
if ($LASTEXITCODE) { throw 'Header extraction failed' }
Push-Location clients
try {
    dotnet pack dotnet/Cae.Client.csproj -c Release "-p:PackageOutputPath=$out/dotnet"
    if ($LASTEXITCODE) { throw 'SDK build failed' }
    dotnet publish ../integration-lab/dotnet-client/Lab.Client.csproj -c Release "-p:PublishDir=$out/dotnet-client" --self-contained false
    if ($LASTEXITCODE) { throw 'Application build failed' }
} finally { Pop-Location }
New-Item -ItemType Directory -Force (Join-Path $out 'admin-client'),(Join-Path $out 'powershell/CAE'),(Join-Path $out 'nodejs'),(Join-Path $out 'cpp/include/nlohmann') | Out-Null
# Separate apphost path gives the test administrator its own enrollment.
Copy-Item (Join-Path $out 'dotnet-client/*') -Destination (Join-Path $out 'admin-client')
Copy-Item clients/powershell/* -Destination (Join-Path $out 'powershell/CAE')
Copy-Item clients/dotnet/bin/Release/net8.0-windows/Cae.Client.dll -Destination (Join-Path $out 'powershell/CAE')
Copy-Item clients/nodejs/index.js,clients/nodejs/worker.js,clients/nodejs/index.d.ts,clients/nodejs/package.json,LICENSE -Destination (Join-Path $out 'nodejs')
Copy-Item clients/cpp/cae_client.hpp -Destination (Join-Path $out 'cpp/include')
Copy-Item (Join-Path $deps 'json.hpp') -Destination (Join-Path $out 'cpp/include/nlohmann')
# JSON's single header contains its full MIT license notice; Node headers are build-only.
Copy-Item (Join-Path $deps 'JSON-LICENSE') -Destination (Join-Path $out 'nodejs/THIRD-PARTY.txt')
Copy-Item (Join-Path $deps 'JSON-LICENSE') -Destination (Join-Path $out 'cpp/THIRD-PARTY.txt')
Copy-Item LICENSE -Destination (Join-Path $out 'cpp')
$vswhere = "${env:ProgramFiles(x86)}/Microsoft Visual Studio/Installer/vswhere.exe"
$vs = & $vswhere -latest -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
if (-not $vs) { throw 'MSVC C++ build tools and Windows SDK are required' }
$devcmd = Join-Path $vs 'Common7/Tools/VsDevCmd.bat'
$toolEnvironment = & cmd.exe /d /s /c "`"$devcmd`" -arch=x64 -host_arch=x64 >nul && set"
foreach ($line in $toolEnvironment) {
    if ($line -match '^(INCLUDE|LIB|LIBPATH|PATH)=(.*)$') {
        [Environment]::SetEnvironmentVariable($Matches[1], $Matches[2], 'Process')
    }
}
clang++ -std=c++20 -O2 -Wall -Wextra -Werror -fuse-ld=lld -Iclients/cpp "-I$deps/include" integration-lab/cpp-client/main.cpp -o (Join-Path $out 'CAE-Cpp-Client.exe') -ladvapi32 -lbcrypt
if ($LASTEXITCODE) { throw 'C++ application build failed' }
clang++ -std=c++20 -O2 -Wall -Wextra -Werror -shared -fuse-ld=lld -DNAPI_VERSION=8 -DNODE_GYP_MODULE_NAME=cae_native -Iclients/cpp "-I$deps/include" "-I$deps/node-v26.8.1/include/node" clients/nodejs/native.cpp clients/nodejs/windows_host.cpp (Join-Path $deps 'node.lib') -o (Join-Path $out 'nodejs/cae_native.node') -ladvapi32 -lbcrypt -ldelayimp '-Wl,/delayload:node.exe'
if ($LASTEXITCODE) { throw 'Node-API build failed' }
Push-Location (Join-Path $out 'nodejs')
try { npm.cmd pack --ignore-scripts; if ($LASTEXITCODE) { throw 'Node package failed' } } finally { Pop-Location }
./.venv/Scripts/python.exe -m build clients/python --no-isolation --outdir (Join-Path $out 'python')
if ($LASTEXITCODE) { throw 'Python SDK build failed' }
Write-Output "Client artifacts: $out (existing broker not rebuilt)"
