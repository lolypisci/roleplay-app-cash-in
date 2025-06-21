@echo off
setlocal enabledelayedexpansion

:askmsg
echo Enter commit message:
set /p msg=
if "%msg%"=="" (
    echo Commit message cannot be empty. Please enter a message.
    goto askmsg
)

echo.
echo Commit message: "!msg!"
set /p confirm="Is this OK? (Y/N): "
if /I not "!confirm!"=="Y" (
    echo Aborting commit.
    pause
    exit /b 1
)

:confirmAdd
echo.
set /p confirmAdd="Do you want to add all changes (git add .)? (Y/N): "
if /I "!confirmAdd!"=="Y" (
    echo Adding changes...
    git add .
    if errorlevel 1 (
        echo Error adding files. Aborting.
        pause
        exit /b 1
    )
) else (
    echo Skipping git add.
)

:confirmCommit
echo.
set /p confirmCommit="Do you want to commit changes now? (Y/N): "
if /I "!confirmCommit!"=="Y" (
    echo Committing changes...
    git commit -m "!msg!"
    if errorlevel 1 (
        echo No changes to commit or error during commit.
        set /p cont="Continue anyway? (Y/N): "
        if /I not "!cont!"=="Y" (
            echo Aborting.
            pause
            exit /b 1
        )
    ) else (
        echo Commit successful.
    )
) else (
    echo Skipping commit.
)

:confirmPull
echo.
set /p confirmPull="Do you want to pull latest changes with rebase? (Y/N): "
if /I "!confirmPull!"=="Y" (
    echo Pulling latest changes...
    git pull --rebase
    if errorlevel 1 (
        echo Error during pull. Please resolve conflicts manually.
        pause
        exit /b 1
    )
    echo Pull successful.
) else (
    echo Skipping pull.
)

:confirmPush
echo.
set /p confirmPush="Do you want to push changes to remote? (Y/N): "
if /I "!confirmPush!"=="Y" (
    echo Pushing to remote repository...
    git push
    if errorlevel 1 (
        echo Error during push. Check your remote repo and credentials.
        pause
        exit /b 1
    )
    echo Push successful.
) else (
    echo Skipping push.
)

echo.
echo All done!
pause
