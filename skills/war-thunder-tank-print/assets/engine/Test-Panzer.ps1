[CmdletBinding()]
param([string]$FreeCADPython = 'C:\Program Files\FreeCAD 1.0\bin\python.exe')
$ErrorActionPreference = 'Stop'
$taskPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
$taskTools = Join-Path $PSScriptRoot 'tools'
foreach ($taskTest in @('test_pipeline.py','test_package_bambu.py','test_mesh_repair.py','test_prepare_vehicle.py','test_prepare_generic.py','test_combine_plate.py','test_stl_precision.py')) {
    if (-not (Test-Path -LiteralPath (Join-Path $taskTools $taskTest))) { throw "Testdatei fehlt: $taskTest" }
    & $taskPython -m unittest discover -s $taskTools -p $taskTest
    if ($LASTEXITCODE -ne 0) { throw "Test fehlgeschlagen: $taskTest" }
}
& $FreeCADPython (Join-Path $taskTools 'test_make_calibration.py')
if ($LASTEXITCODE -ne 0) { throw 'Kalibrier-Geometrietests fehlgeschlagen.' }
Write-Host 'Software- und Geometrietests bestanden. Physischer Druck separat pruefen.'
