Set-StrictMode -Version Latest
$script:Client = $null
Add-Type -Path (Join-Path $PSScriptRoot 'Cae.Client.dll')

function Connect-CAE {
    [CmdletBinding()]
    param([string]$ConnectionFile = $env:CAE_CONNECTION_FILE, [int]$TimeoutMilliseconds = 35000)
    $script:Client = [Cae.CaeClient]::new($ConnectionFile, $TimeoutMilliseconds)
    $script:Client.ConnectAsync().GetAwaiter().GetResult().GetRawText() | ConvertFrom-Json
}
function Invoke-CAERequest {
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$Operation, [hashtable]$Arguments = @{})
    if ($null -eq $script:Client) { throw 'invalid_configuration' }
    # Serialize as JsonElement to avoid PowerShell ETS members on the wire.
    $document = [System.Text.Json.JsonDocument]::Parse(($Arguments | ConvertTo-Json -Depth 32 -Compress))
    try {
        $script:Client.RequestAsync($Operation, $document.RootElement.Clone()).GetAwaiter().GetResult().GetRawText() |
            ConvertFrom-Json -Depth 64
    } finally { $document.Dispose() }
}
function Get-CAEHealth {
    param([string]$Provider = 'openai', [string]$Profile = 'default')
    Invoke-CAERequest health @{provider=$Provider; profile=$Profile}
}
function Get-CAEModels {
    param([string]$Provider = 'openai', [string]$Profile = 'default')
    Invoke-CAERequest models @{provider=$Provider; profile=$Profile}
}
function Get-CAECapabilities { Invoke-CAERequest providers }
function Get-CAEDiagnostics {
    param([string]$Provider = 'openai', [string]$Profile = 'default')
    Invoke-CAERequest diagnostics @{provider=$Provider; profile=$Profile}
}
Export-ModuleMember -Function Connect-CAE,Invoke-CAERequest,Get-CAEHealth,Get-CAEModels,Get-CAECapabilities,Get-CAEDiagnostics
