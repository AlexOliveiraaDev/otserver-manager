@echo off
setlocal

rem Checa se passou versão
if "%~1"=="" (
    echo Uso: release.bat ^<versao^>
    exit /b 1
)
set VERSION=%~1

rem Atualiza version.py
powershell -Command "(Get-Content version.py) -replace '__version__ = \".*\"', '__version__ = \"%VERSION%\"' | Set-Content version.py -Encoding UTF8"

rem Git
git add .
git commit -m "release v%VERSION%"
git tag v%VERSION%
git push origin HEAD --tags

rem GitHub release
gh release create v%VERSION% --title "v%VERSION%" --notes "Release v%VERSION%"

endlocal
