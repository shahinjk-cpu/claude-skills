@echo off
title GitHub Push - 5101 Skills
cd /d "C:\Users\shahin.karimov\claude-skills"
echo =================================================================
echo  Pushing 5101+ Skills to GitHub Repositories...
echo =================================================================
echo.
echo [1/2] Pushing to origin (shahinkarimov/claude-skills)...
git push origin master
echo.
echo [2/2] Pushing to shahinjk (shahinjk-cpu/claude-skills)...
git push shahinjk master
echo.
echo =================================================================
echo  Done!
echo =================================================================
pause
