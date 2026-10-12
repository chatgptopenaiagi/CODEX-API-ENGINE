param([Parameter(Mandatory)][string]$OutputFile)
$ErrorActionPreference = 'Stop'
Import-Module CAE
if ($OutputFile -eq 'probe') {
    try { $null = Connect-CAE -TimeoutMilliseconds 1000; Write-Output 'ok' }
    catch {
        $errorObject = $_.Exception
        while ($null -ne $errorObject.InnerException) { $errorObject = $errorObject.InnerException }
        if ($errorObject -is [Cae.CaeException]) { Write-Output $errorObject.Code }
        else { Write-Output 'broker_unavailable' }
    }
    exit 0
}
while (-not (Test-Path -LiteralPath ($OutputFile + '.stop'))) {
    try {
        $status = Connect-CAE
        $null = Get-CAEHealth -Provider lab
        $models = Get-CAEModels -Provider lab
        $capabilities = Get-CAECapabilities
        $denied = $false
        $malformed = $false
        try { $null = Invoke-CAERequest stop }
        catch { $denied = $_.Exception.ToString().Contains('access_denied') }
        try { $null = Invoke-CAERequest status @{app='admin'} }
        catch { $malformed = $_.Exception.ToString().Contains('invalid_protocol') }
        $restricted = $false
        try { $null = Invoke-CAERequest chat @{provider='lab'; model='lab-model'; text='test'} }
        catch { $restricted = $_.Exception.ToString().Contains('access_denied') }
        $routing = $null
        if ($env:CAE_LAB_ROUTING -eq '1') {
            $routing = Invoke-CAERequest route @{contract_version=1; capability='chat_generation';
                model='route-model'; input='synthetic'; routing_mode='LOCAL_ONLY'}
            $null = Invoke-CAERequest capabilities
        }
        @{routing=$routing; status=$status; models=$models; capabilities=$capabilities; denied=$denied; malformed=$malformed;
          client_pid=$PID; restricted=$restricted} | ConvertTo-Json -Depth 64 -Compress |
            Set-Content -LiteralPath ($OutputFile + '.new') -Encoding utf8NoBOM
        Move-Item -LiteralPath ($OutputFile + '.new') -Destination $OutputFile -Force
    } catch { } # Next read establishes a fresh authenticated connection.
    Start-Sleep -Milliseconds 500
}
