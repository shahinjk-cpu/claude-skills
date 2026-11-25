@echo off
title AI Agent Skills GitHub Sync
cd /d "C:\Users\shahin.karimov\claude-skills"
echo =================================================================
echo  AI Agent Skills: 1589 Skill GitHub Repozitoriyalarina Gonderilir
echo =================================================================
echo.
echo [1/2] shahinkarimov/claude-skills repozitoriyasina push edilir...
git push origin master
echo.
echo [2/2] shahinjk-cpu/claude-skills repozitoriyasina push edilir...
git push shahinjk master
echo.
echo =================================================================
echo  Emeliyyat basa catdi.
echo =================================================================
pause
