<#
.SYNOPSIS
    Universal AI Skills Hub - Auto-Configuration Script
.DESCRIPTION
    Links all 448+ skills in this repository across all installed AI agents and IDEs:
    - Anthropic Claude (~/.claude/skills)
    - Google Antigravity (~/.gemini/config/skills & ~/.gemini/config/skills.json)
    - OpenAI Codex (~/.codex/skills)
    - Universal Agent Standard (~/.agents/skills)
    - Windsurf / Cascade (~/.codeium/windsurf/skills)
    - Cursor IDE (~/.cursor/rules)
    - GitHub Copilot (~/.copilot)
#>

$repoSkillsDir = Join-Path $PSScriptRoot "skills"
if (-not (Test-Path $repoSkillsDir)) {
    Write-Error "Skills directory not found: $repoSkillsDir"
    exit 1
}

$userProfile = [System.Environment]::GetFolderPath('UserProfile')

# 1. Claude
$claudeSkills = Join-Path $userProfile ".claude\skills"
if (-not (Test-Path $claudeSkills)) { New-Item -ItemType Directory -Path $claudeSkills -Force | Out-Null }

# 2. Antigravity (Google AGY)
$geminiConfig = Join-Path $userProfile ".gemini\config"
if (-not (Test-Path $geminiConfig)) { New-Item -ItemType Directory -Path $geminiConfig -Force | Out-Null }

$geminiSkillsJson = Join-Path $geminiConfig "skills.json"
$skillsJsonContent = @"
{
  "entries": [
    {
      "path": "$($claudeSkills.Replace('\', '/'))"
    },
    {
      "path": "$($userProfile.Replace('\', '/'))/.agents/skills"
    }
  ]
}
"@
Set-Content -Path $geminiSkillsJson -Value $skillsJsonContent -Encoding UTF8

$geminiSkillsJunction = Join-Path $geminiConfig "skills"
if (-not (Test-Path $geminiSkillsJunction)) {
    cmd /c mklink /J "$geminiSkillsJunction" "$claudeSkills" > $null 2>&1
}

# 3. Targets for Directory Junctions
$targets = @(
    $claudeSkills,
    (Join-Path $userProfile ".codex\skills"),
    (Join-Path $userProfile ".agents\skills"),
    (Join-Path $userProfile ".codeium\windsurf\skills")
)

$allSkills = Get-ChildItem -Path $repoSkillsDir -Directory

foreach ($target in $targets) {
    if (-not (Test-Path $target)) { New-Item -ItemType Directory -Path $target -Force | Out-Null }
    
    $created = 0
    foreach ($skill in $allSkills) {
        $dest = Join-Path $target $skill.Name
        if (-not (Test-Path $dest)) {
            cmd /c mklink /J "$dest" "$($skill.FullName)" > $null 2>&1
            $created++
        }
    }
    Write-Host "[OK] Synced $created skills to: $target" -ForegroundColor Green
}

# 4. Cursor Rules
$cursorRulesDir = Join-Path $userProfile ".cursor\rules"
if (-not (Test-Path $cursorRulesDir)) { New-Item -ItemType Directory -Path $cursorRulesDir -Force | Out-Null }
$cursorRuleFile = Join-Path $cursorRulesDir "ai-skills-hub.mdc"
$cursorRuleContent = @"
---
description: Universal AI Skills Hub - 448+ expert engineering, design, gamedev, and architecture skills
globs: *
alwaysApply: true
---

# Universal AI Skills Hub

You have access to 448+ specialized AI skills installed locally at:
- $claudeSkills
- $(Join-Path $userProfile ".agents\skills")

Inspect and load procedures from:
`$claudeSkills\<skill-name>\SKILL.md`
"@
Set-Content -Path $cursorRuleFile -Value $cursorRuleContent -Encoding UTF8
Write-Host "[OK] Configured Cursor IDE global rule: $cursorRuleFile" -ForegroundColor Green

# 5. GitHub Copilot
$copilotDir = Join-Path $userProfile ".copilot"
if (-not (Test-Path $copilotDir)) { New-Item -ItemType Directory -Path $copilotDir -Force | Out-Null }
$copilotFile = Join-Path $copilotDir "copilot-instructions.md"
$copilotContent = @"
# GitHub Copilot - Machine-Local AI Skills Hub

This system has 448+ verified AI skills installed locally at:
- $claudeSkills
- $(Join-Path $userProfile ".agents\skills")

When solving user requests, inspect and follow the specialized workflows documented in:
`$claudeSkills\<skill-name>\SKILL.md`
"@
Set-Content -Path $copilotFile -Value $copilotContent -Encoding UTF8
Write-Host "[OK] Configured GitHub Copilot instructions: $copilotFile" -ForegroundColor Green

Write-Host "`nAll 448+ AI skills are now universally accessible to Claude, Antigravity, Cursor, Windsurf, Codex, and Copilot!" -ForegroundColor Cyan
