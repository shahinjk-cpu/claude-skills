[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Vehicle,
    [ValidateRange(35, 200)][int]$Scale = 72,
    [ValidateSet('all','export','recipe','check-scale','inspect','prepare','package','combine','calibration','check-pantsir')]
    [string]$Stage = 'all',
    [ValidateSet('a1mini_02_pla')][string]$Profile = 'a1mini_02_pla',
    [string]$DisplayName
)
$ErrorActionPreference = 'Stop'
$taskPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $taskPython)) {
    throw 'Projektumgebung fehlt. Zuerst Setup-Panzer.ps1 ausfuehren.'
}
$taskArgs = @((Join-Path $PSScriptRoot 'tools\pipeline.py'), '--vehicle', $Vehicle, '--scale', $Scale, '--stage', $Stage, '--profile', $Profile)
if ($DisplayName) { $taskArgs += @('--display-name', $DisplayName) }
& $taskPython @taskArgs
$pipelineExit = $LASTEXITCODE
# Outcome comes from logs\latest_run.json, not from console text.
& $taskPython (Join-Path $PSScriptRoot 'tools\run_status.py')
$statusExit = $LASTEXITCODE
if ($pipelineExit -ne 0 -or $statusExit -ne 0) {
    throw "Pipeline fehlgeschlagen (Exit $pipelineExit, Status $statusExit). Details in logs\latest_run.json."
}
