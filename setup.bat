@echo off
chcp 65001 >nul
title AI Agent Skills - Universal 1-Click Bootstrap Installer
echo =================================================================
echo   🧠 UNIVERSAL AI AGENT SKILLS BOOTSTRAPPER (5,101+ SKILLS)
echo =================================================================
echo.
echo [1/4] Detecting AI Agent environments...

set "SRC_DIR=%~dp0"
set "SKILLS_SRC=%SRC_DIR%skills"
set "USER_HOME=%USERPROFILE%"

set "GEMINI_DIR=%USER_HOME%\.gemini\config\skills"
set "CLAUDE_DIR=%USER_HOME%\.claude\skills"
set "CURSOR_DIR=%USER_HOME%\.cursor\skills"
set "AGENTS_DIR=%USER_HOME%\.agents\skills"
set "CODEX_DIR=%USER_HOME%\.codex\skills"

echo [2/4] Creating local environment directories...
if not exist "%GEMINI_DIR%" mkdir "%GEMINI_DIR%"
if not exist "%CLAUDE_DIR%" mkdir "%CLAUDE_DIR%"
if not exist "%CURSOR_DIR%" mkdir "%CURSOR_DIR%"
if not exist "%AGENTS_DIR%" mkdir "%AGENTS_DIR%"
if not exist "%CODEX_DIR%" mkdir "%CODEX_DIR%"

echo [3/4] Linking / Syncing all 5,101+ skills across all agent hubs...
powershell -NoProfile -ExecutionPolicy Bypass -Command "& '%SRC_DIR%setup.ps1'"

echo.
echo =================================================================
echo   ✅ Bootstrap Complete! All 5,101+ skills & Auto-Router are active!
echo =================================================================
pause
