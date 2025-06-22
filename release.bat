@echo off
REM Change to your project directory (if needed)
cd /d %~dp0

echo Adding all files...
git add .

echo Enter commit message:
set /p msg="> "
if "%msg%"=="" set msg=update

echo Committing with message: %msg%
git commit -m "%msg%"

echo Pushing to origin...
git push origin main

pause
