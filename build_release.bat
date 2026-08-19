@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

set APP_NAME=Form@Prospect
set SPEC_FILE=formaprospect.spec
set RELEASE_DIR=release\Form@Prospect
set RELEASE_BASE_URL=https://forma-prof.fr/formaprospect/releases

REM Dossier tres court utilise uniquement par Inno Setup.
REM Important : Playwright/Chromium contient des chemins tres profonds.
set INNO_STAGE=%TEMP%\FP_BUILD\Form@Prospect

cls
echo ============================================================
echo  Form@Prospect - Build Windows + Installateur + Mise a jour
echo ============================================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo ERREUR : Python est introuvable dans le PATH.
    pause
    exit /b 1
)

if not exist "VERSION" echo 1.0.0> VERSION
set /p APP_VERSION=<VERSION
set APP_VERSION=!APP_VERSION: =!

if "!APP_VERSION!"=="" (
    echo ERREUR : VERSION est vide.
    pause
    exit /b 1
)

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

echo [1/9] Version : !APP_VERSION!
echo #define MyAppVersion "!APP_VERSION!"> "installer\version.iss"

echo.
echo [2/9] Verification de Python...
python --version
if errorlevel 1 pause & exit /b 1

echo.
echo [3/9] Verification des dependances de build...
python -m pip install -r requirements-build.txt
if errorlevel 1 (
    echo ERREUR : installation des dependances impossible.
    pause
    exit /b 1
)

echo.
echo [4/9] Nettoyage des anciens builds...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "release" rmdir /s /q "release"
if exist "release_publish" rmdir /s /q "release_publish"
if exist "installer\output" rmdir /s /q "installer\output"
if exist "%TEMP%\FP_BUILD" rmdir /s /q "%TEMP%\FP_BUILD"
mkdir "release"

echo.
echo [5/9] Creation de Form@Prospect.exe...
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

robocopy "dist\Form@Prospect" "%RELEASE_DIR%" /E /R:2 /W:1 >nul
set COPY_RC=!ERRORLEVEL!
if !COPY_RC! GEQ 8 (
    echo ERREUR : copie du dossier release impossible ^(code !COPY_RC!^).
    pause
    exit /b !COPY_RC!
)

echo.
echo [6/9] Preparation d'un chemin court pour Inno Setup...
mkdir "%TEMP%\FP_BUILD" >nul 2>nul
robocopy "%RELEASE_DIR%" "%INNO_STAGE%" /E /R:2 /W:1 >nul
set STAGE_RC=!ERRORLEVEL!
if !STAGE_RC! GEQ 8 (
    echo ERREUR : preparation du dossier temporaire impossible ^(code !STAGE_RC!^).
    pause
    exit /b !STAGE_RC!
)

if not exist "%INNO_STAGE%\Form@Prospect.exe" (
    echo ERREUR : Form@Prospect.exe absent du dossier temporaire.
    pause
    exit /b 1
)

echo Dossier Inno court : %INNO_STAGE%

echo.
echo [7/9] Recherche de Inno Setup...
set ISCC=
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe
if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe

if not defined ISCC (
    echo ERREUR : Inno Setup 6 est introuvable.
    echo Installe Inno Setup 6 puis relance ce fichier.
    pause
    exit /b 1
)

echo.
echo [8/9] Creation de l'installateur...
"%ISCC%" /DSourceDir="%INNO_STAGE%" "installer\Form@Prospect_Setup.iss"
if errorlevel 1 (
    echo ERREUR : Inno Setup a echoue.
    echo.
    echo Le dossier temporaire a ete conserve pour diagnostic :
    echo %INNO_STAGE%
    pause
    exit /b 1
)

set SETUP_FILE=installer\output\Form@Prospect_Setup_v!APP_VERSION!.exe
if not exist "!SETUP_FILE!" (
    echo ERREUR : installateur introuvable : !SETUP_FILE!
    pause
    exit /b 1
)

echo.
echo [9/9] Preparation du paquet de publication...
python "tools\build_update_manifest.py" ^
  --version "!APP_VERSION!" ^
  --installer "!SETUP_FILE!" ^
  --base-url "%RELEASE_BASE_URL%" ^
  --notes-file "installer\release_notes.txt" ^
  --output-dir "release_publish"

if errorlevel 1 (
    echo ERREUR : creation du manifeste de mise a jour impossible.
    pause
    exit /b 1
)

REM Nettoyage du staging seulement si tout s'est bien passe.
if exist "%TEMP%\FP_BUILD" rmdir /s /q "%TEMP%\FP_BUILD"

echo.
echo ============================================================
echo  BUILD TERMINE AVEC SUCCES
echo ============================================================
echo.
echo Version             : !APP_VERSION!
echo Application portable: %RELEASE_DIR%\Form@Prospect.exe
echo Installateur        : !SETUP_FILE!
echo Publication Web     : release_publish\
echo.
echo Pour publier la mise a jour, envoyer le contenu de
echo release_publish\ vers :
echo %RELEASE_BASE_URL%/
echo.
pause
