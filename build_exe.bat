@echo off
echo ============================================
echo   Build GLPI Label Generator - EXE portable
echo ============================================
echo.

REM Install dependencies
echo [1/2] Installation des dependances...
pip install -r requirements.txt
echo.

REM Build exe
echo [2/2] Construction de l'exe...
pyinstaller --onefile --windowed --name "GLPI_Labels" ^
    --collect-all customtkinter ^
    --hidden-import PIL ^
    --hidden-import PIL._tkinter_finder ^
    glpi_labels_gui.py

echo.
echo ============================================
if exist "dist\GLPI_Labels.exe" (
    echo   [OK] dist\GLPI_Labels.exe cree !
    echo   Copie le .exe ou tu veux, il est portable.
) else (
    echo   [ERREUR] Le build a echoue.
)
echo ============================================
pause
