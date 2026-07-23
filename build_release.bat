@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

set APP_NAME=Form@Prospect
set SPEC_FILE=formaprospect.spec
set RELEASE_DIR=release\Form@Prospect

cls
echo ==========================================
echo  Form@Prospect - Build Windows V1.1-G Cloud Integration
echo ==========================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo ERREUR : Python est introuvable dans le PATH.
    pause
    exit /b 1
)

if not exist "VERSION" echo 1.0.0> VERSION
if not exist "%SPEC_FILE%" (
    echo ERREUR : %SPEC_FILE% introuvable.
    pause
    exit /b 1
)
if not exist "assets\icons\formaprospect.ico" (
    echo ERREUR : assets\icons\formaprospect.ico introuvable.
    pause
    exit /b 1
)

echo [1/5] Verification de Python...
python --version
if errorlevel 1 pause & exit /b 1

echo.
echo [2/5] Installation / verification des dependances de build...
python -m pip install --upgrade pip
python -m pip install -r requirements-build.txt
if errorlevel 1 (
    echo ERREUR : installation des dependances impossible.
    pause
    exit /b 1
)

echo.
echo [3/5] Nettoyage des anciens builds...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "release" rmdir /s /q "release"
mkdir "release"

echo.
echo [4/5] Creation de l'executable avec icone...
python -m PyInstaller --clean --noconfirm "%SPEC_FILE%"
if errorlevel 1 (
    echo ERREUR : PyInstaller a echoue.
    pause
    exit /b 1
)

if not exist "dist\Form@Prospect\Form@Prospect.exe" (
    echo ERREUR : executable introuvable.
    pause
    exit /b 1
)

echo.
echo [5/5] Preparation du dossier release...
for %%F in (company.json offers.json funding.json objections.json scripts.json faq.json case_studies.json) do (
    if not exist "dist\Form@Prospect\_internal\services\ai\knowledge\%%F" (
        echo ERREUR : fichier embarque introuvable : %%F
        pause
        exit /b 1
    )
)

robocopy "dist\Form@Prospect" "%RELEASE_DIR%" /E /R:2 /W:1 >nul
set COPY_RC=!ERRORLEVEL!
if !COPY_RC! GEQ 8 (
    echo ERREUR : copie du dossier release impossible ^(code !COPY_RC!^).
    pause
    exit /b !COPY_RC!
)

echo.
echo ==========================================
echo Build termine avec succes.
echo Executable portable : %RELEASE_DIR%\Form@Prospect.exe
echo ==========================================
echo.
echo Si l'icone ne change pas tout de suite dans Windows, c'est souvent le cache d'icones.
echo Renomme temporairement le dossier release ou redemarre l'Explorateur Windows.
echo.
pause
