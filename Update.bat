@echo off
setlocal

:: Define the repository URL and temporary folder
set "REPO_URL=https://github.com/theo-saminadin-artfx/RendermanDenoiseUI.git"
set "TEMP_DIR=%~dp0\temp"
set "TARGET_DIR=%~dp0"

:: Check if Git is installed
where git >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Git is not installed.
    pause
    exit /b 1
)

:: Add the directory to Git's safe list for all user
git config --global --add safe.directory %TARGET_DIR%


:: Check if it's already a Git repository
if exist ".git" (
   echo Updating existing repository...
   git pull origin main

   git checkout -- .
   echo Update completed!
   pause
   exit /b 0
)

:: Remove previous temp directory if it exists
if exist "%TEMP_DIR%" rd /s /q "%TEMP_DIR%"

:: Clone the repository into a temporary folder
echo Cloning repository...
git clone --depth 1 "%REPO_URL%" "%TEMP_DIR%"

:: Check if cloning was successful
if not exist "%TEMP_DIR%\.git" (
    echo Cloning failed!
    pause
    exit /b 1
)


:: Move all files from the temporary folder to the target directory
echo Moving files...
xcopy "%TEMP_DIR%\*" "%TARGET_DIR%\" /E /H /C /Y /Q

:: Clean up
rd /s /q "%TEMP_DIR%"

echo Update completed!
pause
exit /b 0