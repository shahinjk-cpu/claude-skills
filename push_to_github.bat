@echo off
chcp 65001 >nul
title AI Agent Skills GitHub Sync (3,876+ Skills)
cd /d "C:\Users\shahin.karimov\claude-skills"
echo =================================================================
echo  AI Agent Skills: Bütün Skill-lər GitHub-a Göndərilir
echo =================================================================
echo.
echo [1/2] shahinkarimov/claude-skills repozitoriyasına push edilir...
git push origin master
echo.
echo [2/2] shahinjk-cpu/claude-skills repozitoriyasına push edilir...
git push shahinjk master
echo.
echo =================================================================
echo  Əməliyyat başa çatdı! Bütün dəyişikliklər GitHub-da yeniləndi.
echo =================================================================
pause
