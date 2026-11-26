[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$taskVendor = Join-Path $PSScriptRoot 'vendor'
$taskExporter = Join-Path $taskVendor 'wt_asset_explorer'
$taskCommit = '99c794ab102785c39e628033a09bf4ff18dbe64e'
$taskUv = (Get-Command uv -ErrorAction Stop).Source
$taskGit = (Get-Command git -ErrorAction Stop).Source
$env:UV_PYTHON_INSTALL_DIR = Join-Path $PSScriptRoot 'runtime\python'
$env:UV_CACHE_DIR = Join-Path $PSScriptRoot 'runtime\uv-cache'
New-Item -ItemType Directory -Path $taskVendor -Force | Out-Null
if (-not (Test-Path -LiteralPath $taskExporter)) {
    & $taskGit clone --branch testing https://github.com/NotNekroz/wt-asset-explorer.git $taskExporter
    if ($LASTEXITCODE -ne 0) { throw 'Exporter-Download fehlgeschlagen.' }
    & $taskGit -C $taskExporter checkout $taskCommit
    if ($LASTEXITCODE -ne 0) { throw 'Exporter-Version nicht verfuegbar.' }
}
$taskActualCommit = (& $taskGit -C $taskExporter rev-parse HEAD).Trim()
if ($taskActualCommit -ne $taskCommit) { throw "Exporter-Version weicht ab: $taskActualCommit" }
$taskWtExe = Join-Path $taskVendor 'wt_ext_cli-0.6.6\wt_ext_cli.exe'
if (-not (Test-Path -LiteralPath $taskWtExe)) {
    $taskZip = Join-Path $taskVendor 'wt_ext_cli-0.6.6-win64.zip'
    Invoke-WebRequest -Uri 'https://github.com/Warthunder-Open-Source-Foundation/wt_ext_cli/releases/download/v0.6.6/wt_ext_cli-x86_64-pc-windows-msvc.zip' -OutFile $taskZip
    Expand-Archive -LiteralPath $taskZip -DestinationPath (Join-Path $taskVendor 'wt_ext_cli-0.6.6') -Force
}
$taskPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $taskPython)) {
    & $taskUv venv --python 3.11 (Join-Path $PSScriptRoot '.venv')
    if ($LASTEXITCODE -ne 0) { throw 'Python-Umgebung konnte nicht erstellt werden.' }
}
& $taskUv pip sync --python $taskPython (Join-Path $PSScriptRoot 'requirements-lock.txt')
if ($LASTEXITCODE -ne 0) { throw 'Abhaengigkeiten konnten nicht installiert werden.' }
& $taskPython -c 'import bpy, trimesh, PySide6; print("Bereit: Blender", bpy.app.version_string)'
if ($LASTEXITCODE -ne 0) { throw 'Laufzeitpruefung fehlgeschlagen.' }
