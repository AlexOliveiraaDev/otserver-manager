@echo off
setlocal

rem Check if version argument is provided
if "%~1"=="" (
    echo Usage: release.bat ^<version^>
    exit /b 1
)
set VERSION=%~1

rem Verify if version.py exists
if not exist "version.py" (
    echo Error: version.py not found in the current directory
    exit /b 1
)

rem Update version.py
powershell -Command "$content = Get-Content version.py -Raw; if ($content -match '__version__ *= *\""[^\""]*\""') { $content -replace '__version__ *= *\""[^\""]*\""', '__version__ = \""%VERSION%\""' | Set-Content version.py -Encoding UTF8 } else { Write-Error 'Version pattern not found in version.py'; exit 1 }"

rem Check if PowerShell command was successful
if %ERRORLEVEL% neq 0 (
    echo Error: Failed to update version.py
    exit /b 1
)

rem Verify the content of version.py
findstr /C:"__version__ = \"%VERSION%\"" version.py >nul
if %ERRORLEVEL% neq 0 (
    echo Error: version.py was not updated to %VERSION%
    type version.py
    exit /b 1
)

rem Git operations
git add .
git commit -m "release v%VERSION%"
git tag v%VERSION%
git push origin HEAD --tags

rem GitHub release
gh release create v%VERSION% --title "v%VERSION%" --notes "Release v%VERSION%"

endlocal