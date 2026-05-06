@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

set "PY_CMD=py -3"
where py >nul 2>&1
if errorlevel 1 set "PY_CMD=python"

echo ===============================================
echo  GLPI Labels CLI - Test rapide (mode demo)
echo ===============================================
echo.

echo [1/4] Liste complete
%PY_CMD% glpi_labels.py --list
if errorlevel 1 goto :error
echo.

echo [2/4] Filtre lieu + type
%PY_CMD% glpi_labels.py --list --type Computer --lieu Chambon
if errorlevel 1 goto :error
echo.

echo [3/4] Filtre utilisateur
%PY_CMD% glpi_labels.py --list --user Atelier
if errorlevel 1 goto :error
echo.

echo [4/4] Generation PDF demo
%PY_CMD% glpi_labels.py --output "%SCRIPT_DIR%glpi_etiquettes_DEMO_test.bat.pdf"
if errorlevel 1 goto :error
echo.

echo OK - Tous les tests se sont termines correctement.
goto :end

:error
echo.
echo ERREUR - Un test a echoue. Code: %errorlevel%
exit /b %errorlevel%

:end
endlocal

