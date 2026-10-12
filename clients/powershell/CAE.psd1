@{
    RootModule = 'CAE.psm1'
    ModuleVersion = '0.4.0'
    GUID = '29f32fc7-dd47-4f4b-b80a-7bb4979d3974'
    Author = 'CAE contributors'
    Description = 'Windows named-pipe client for CAE protocol v1'
    PowerShellVersion = '7.4'
    FunctionsToExport = @('Connect-CAE','Invoke-CAERequest','Get-CAEHealth','Get-CAEModels','Get-CAECapabilities','Get-CAEDiagnostics')
    CmdletsToExport = @()
    VariablesToExport = @()
    AliasesToExport = @()
}
