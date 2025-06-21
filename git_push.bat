@echo off
setlocal enabledelayedexpansion

echo Enter commit message:
set /p msg=

if "%msg%"=="" (
    echo Commit message cannot be empty. Exiting.
    pause
    exit /b 1
)

echo Adding changes...
git add .
if errorlevel 1 (
    echo Error adding files. Exiting.
    pause
    exit /b 1
)

echo Committing changes...
git commit -m "!msg!"
if errorlevel 1 (
    echo Error during commit. Possibly no changes to commit.
) else (
    echo Commit successful.
)

echo Pulling latest changes with rebase...
git pull --rebase
if errorlevel 1 (
    echo Error during pull. Please resolve conflicts manually.
    pause
    exit /b 1
) else (
    echo Pull successful.
)

echo Pushing to remote repository...
git push
if errorlevel 1 (
    echo Error during push. Please check your remote repository and credentials.
    pause
    exit /b 1
) else (
    echo Push successful.
)

echo All done!
pause
