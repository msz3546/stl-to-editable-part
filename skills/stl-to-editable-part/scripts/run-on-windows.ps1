[CmdletBinding()]
param(
    [switch]$Check,
    [string]$Source,
    [string]$Destination,
    [string]$WorkDir,
    [ValidateSet('mm','cm','m','in','ft')][string]$Units = 'mm',
    [ValidateSet('auto','require','keep')][string]$Holes = 'auto',
    [double]$HoleDiameterMm,
    [string]$Python,
    [string]$OcpPath,
    [string]$SwRoot,
    [string]$Template,
    [string]$ImportedPart,
    [string]$Plan,
    [switch]$PrepareOnly,
    [string]$ReuseVerified,
    [string]$EditDimension,
    [switch]$NoPreview
)

$ErrorActionPreference = 'Stop'
$skillRoot = Split-Path -Parent $PSScriptRoot
$skillsRoot = Split-Path -Parent $skillRoot
$dshRoot = $env:DSH_HOME
if (-not $dshRoot) {
    if ((Split-Path -Leaf $skillsRoot) -eq 'skills' -and (Split-Path -Leaf (Split-Path -Parent $skillsRoot)) -eq '.dsh') {
        $dshRoot = Split-Path -Parent $skillsRoot
    } else {
        $dshRoot = Join-Path $env:USERPROFILE '.dsh'
    }
}

if (-not $Python) {
    $bundled = Join-Path $dshRoot 'dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe'
    if (Test-Path -LiteralPath $bundled -PathType Leaf) {
        $Python = $bundled
    } else {
        $command = Get-Command python.exe -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
        if (-not $command) { throw 'Python was not found. Supply -Python with the full path to python.exe.' }
        $Python = $command.Source
    }
}
if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) { throw "Python path does not exist: $Python" }
$Python = (Resolve-Path -LiteralPath $Python).ProviderPath
if (-not $OcpPath) {
    $localOcp = Join-Path $dshRoot 'skill-dependencies\stl-to-editable-part'
    if (Test-Path -LiteralPath (Join-Path $localOcp 'OCP\__init__.py') -PathType Leaf) { $OcpPath = $localOcp }
}

if ($Check) {
    $checkCode = 'import sys; sys.path[:0] = sys.argv[1:]; import numpy, OCP; print(sys.executable); print(numpy.__name__, numpy.__version__, OCP.__name__, OCP.__version__)'
    $checkArguments = @('-X','utf8','-B','-c',$checkCode)
    if ($OcpPath) { $checkArguments += $OcpPath }
    & $Python @checkArguments
    exit $LASTEXITCODE
}
if (-not $Source) { throw 'Supply -Source, or run with -Check.' }
$entrypoint = Join-Path $PSScriptRoot 'convert_part.py'
$options = @('-X','utf8','-B',$entrypoint,$Source)
if ($Destination) { $options += $Destination }
$options += @('--units',$Units,'--holes',$Holes)
if ($PrepareOnly) { $options += '--prepare-only' }
$forward = @{
    '--work-dir' = $WorkDir
    '--ocp-path' = $OcpPath
    '--sw-root' = $SwRoot
    '--template' = $Template
    '--imported-part' = $ImportedPart
    '--plan' = $Plan
    '--reuse-verified' = $ReuseVerified
    '--edit-dimension' = $EditDimension
}
foreach ($pair in $forward.GetEnumerator()) {
    if ($pair.Value) { $options += @($pair.Key, $pair.Value) }
}
if ($PSBoundParameters.ContainsKey('HoleDiameterMm')) {
    $options += @('--hole-diameter-mm', $HoleDiameterMm.ToString([Globalization.CultureInfo]::InvariantCulture))
}
if ($NoPreview) { $options += '--no-preview' }
& $Python @options
exit $LASTEXITCODE
