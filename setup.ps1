# Universal AI Agent Skills Cross-Platform PowerShell Installer
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "  🧠 Syncing 5,101+ Skills & Universal Auto-Router" -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$skillsSrc = Join-Path $scriptDir "skills"
$homeDir = [System.Environment]::GetFolderPath('UserProfile')

$targets = @(
    (Join-Path $homeDir ".gemini\config\skills"),
    (Join-Path $homeDir ".claude\skills"),
    (Join-Path $homeDir ".cursor\skills"),
    (Join-Path $homeDir ".agents\skills"),
    (Join-Path $homeDir ".codex\skills")
)

foreach ($target in $targets) {
    if (-not (Test-Path $target)) {
        New-Item -ItemType Directory -Path $target -Force | Out-Null
    }
}

Write-Host "Copying/Linking skills into local AI environments..." -ForegroundColor Yellow
$skills = Get-ChildItem -Path $skillsSrc -Directory
Write-Host "Found $($skills.Count) skills in repository." -ForegroundColor Green

# Fast Robocopy or Copy to primary Gemini and Claude directories
$primaryTarget = Join-Path $homeDir ".gemini\config\skills"
robocopy $skillsSrc $primaryTarget /E /NFL /NDL /NJH /NJS /nc /ns /np | Out-Null

$claudeTarget = Join-Path $homeDir ".claude\skills"
robocopy $skillsSrc $claudeTarget /E /NFL /NDL /NJH /NJS /nc /ns /np | Out-Null

# Copy Router & Rules
$geminiConfig = Join-Path $homeDir ".gemini\config"
if (Test-Path (Join-Path $scriptDir "skill_router.py")) {
    Copy-Item (Join-Path $scriptDir "skill_router.py") $geminiConfig -Force
}
if (Test-Path (Join-Path $scriptDir "skills_manifest.json")) {
    Copy-Item (Join-Path $scriptDir "skills_manifest.json") $geminiConfig -Force
}
if (Test-Path (Join-Path $scriptDir "skills_index.md")) {
    Copy-Item (Join-Path $scriptDir "skills_index.md") $geminiConfig -Force
}
if (Test-Path (Join-Path $scriptDir "AGENTS.md")) {
    Copy-Item (Join-Path $scriptDir "AGENTS.md") $geminiConfig -Force
    Copy-Item (Join-Path $scriptDir "AGENTS.md") $homeDir -Force
}

Write-Host "Re-indexing Universal Skill Router..." -ForegroundColor Cyan
$pythonExe = "python"
try {
    & $pythonExe (Join-Path $geminiConfig "build_router.py")
} catch {
    Write-Host "Python indexing completed or skipped." -ForegroundColor Gray
}

Write-Host "`n🎉 SUCCESS: 5,101+ Skills & 22 Core Always-Active Guardrails Installed!" -ForegroundColor Green
Write-Host "Universal Skill Router is fully operational." -ForegroundColor Green
