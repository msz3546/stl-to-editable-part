# Run in Windows PowerShell 5.1 with -STA.
[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidateSet('Probe','Prepare','Define','Rebuild','RebuildValidate','Audit','Validate')]
    [string]$Mode,
    [string]$Source,
    [string]$Destination,
    [string]$Baseline,
    [string]$SwRoot,
    [string]$Template,
    [ValidateRange(0.0,1000000.0)][double]$VolumeToleranceMm3 = 0.01,
    [ValidateRange(0.0,1000.0)][double]$BoundsToleranceMm = 0.001,
    [string]$EditDimension,
    [ValidateRange(0.5,1.5)][double]$EditFactor = 0.95,
    [string]$Preview
)

$ErrorActionPreference = 'Stop'
if ($PSVersionTable.PSEdition -ne 'Desktop' -or [Threading.Thread]::CurrentThread.GetApartmentState() -ne 'STA') {
    throw 'Run with Windows PowerShell 5.1 in STA mode (powershell.exe -STA).'
}

function Get-ExistingPath([string]$Path, [string]$Label) {
    if (-not $Path -or -not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw "Supply a readable $Label file." }
    return (Resolve-Path -LiteralPath $Path).ProviderPath
}

function Get-NewPath([string]$Path, [string]$Extension) {
    if (-not $Path -or [IO.Path]::GetExtension($Path) -ne $Extension) { throw "Supply a new $Extension output path." }
    $resolved = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($Path)
    if (Test-Path -LiteralPath $resolved) { throw "Output already exists: $resolved" }
    if (-not [IO.Directory]::Exists([IO.Path]::GetDirectoryName($resolved))) { throw "Create the output folder before running." }
    return $resolved
}

if ($Mode -ne 'Probe') {
    $Source = Get-ExistingPath $Source 'source'
    $extension = [IO.Path]::GetExtension($Source).ToLowerInvariant()
    $expected = if ($Mode -in @('Rebuild','RebuildValidate')) { @('.json') } elseif ($Mode -eq 'Prepare') { @('.step','.stp','.sldprt') } else { @('.sldprt') }
    if ($extension -notin $expected) { throw "Unexpected source extension for ${Mode}: $extension" }
}
if ($Mode -in @('Prepare','Define','Rebuild','RebuildValidate')) { $Destination = Get-NewPath $Destination '.sldprt' }
if ($Mode -in @('Validate','RebuildValidate')) {
    $Baseline = Get-ExistingPath $Baseline 'baseline SLDPRT'
    if ([IO.Path]::GetExtension($Baseline) -ne '.sldprt' -or $Baseline -in @($Source,$Destination)) { throw 'Use a distinct, imported baseline SLDPRT.' }
    if ($Preview) { $Preview = Get-NewPath $Preview '.bmp' }
    if ($EditDimension -and $EditFactor -eq 1) { throw 'Select an edit factor other than 1.' }
}
if ($Template) { $Template = Get-ExistingPath $Template 'part template' }
if (-not $SwRoot) {
    $SwRoot = Get-ChildItem -LiteralPath 'HKLM:\SOFTWARE\SolidWorks' |
        Where-Object PSChildName -Match '^SOLIDWORKS \d{4}$' |
        Sort-Object PSChildName -Descending |
        ForEach-Object { (Get-ItemProperty -LiteralPath (Join-Path $_.PSPath 'Setup') -Name 'SolidWorks Folder' -ErrorAction SilentlyContinue).'SolidWorks Folder' } |
        Where-Object { $_ -and (Test-Path -LiteralPath (Join-Path $_ 'SLDWORKS.exe') -PathType Leaf) } |
        Select-Object -First 1
}
if (-not $SwRoot) { throw 'SolidWorks installation not found. Supply -SwRoot.' }
$interop = Join-Path $SwRoot 'api\redist'
$assemblies = @('sldworks','swconst') | ForEach-Object { Join-Path $interop "SolidWorks.Interop.$_.dll" }
if (-not ('SolidWorksPart' -as [type])) {
    foreach ($assembly in $assemblies) { Add-Type -Path $assembly }
    $sourceCode = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'SolidWorksPart.cs') -Raw -Encoding UTF8
    Add-Type -TypeDefinition $sourceCode -ReferencedAssemblies ($assemblies + 'System.Core.dll' + 'System.Web.Extensions.dll')
}
[SolidWorksPart]::Run($Mode,$Source,$Destination,$Baseline,$Template,
    $VolumeToleranceMm3,$BoundsToleranceMm,$EditDimension,$EditFactor,$Preview)
