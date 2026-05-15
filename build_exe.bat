@echo off
REM build_exe.bat — Empaqueta gui_app.py como .exe portable
REM Requiere: pip install pyinstaller

title Empaquetando Generador PDFs

echo ============================================
echo  Empaquetando Generador de PDFs...
echo ============================================
echo.

REM Activar entorno virtual si existe
if exist ".venv\Scripts\Activate.bat" (
    call .venv\Scripts\Activate.bat
)

REM Verificar pyinstaller (debe estar en requirements.txt)
pip show pyinstaller >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: PyInstaller no esta instalado.
    echo Ejecuta primero: pip install -r requirements.txt
    pause
    exit /b 1
)

REM Limpiar builds anteriores
if exist "dist" rmdir /s /q dist
if exist "build" rmdir /s /q build

REM Empaquetar
echo.
echo Ejecutando PyInstaller...
pyinstaller --onefile --windowed --name "GenerarPDFs" ^
    --add-data ".agents\skills\canvas-design\canvas-fonts;canvas-fonts" ^
    --hidden-import tkinter ^
    --hidden-import tkinter.filedialog ^
    --hidden-import tkinter.messagebox ^
    --hidden-import pandas ^
    --hidden-import reportlab ^
    --hidden-import tqdm ^
    gui_app.py

echo.
if exist "dist\GenerarPDFs.exe" (
    echo ============================================
    echo  LISTO: dist\GenerarPDFs.exe
    echo ============================================
    echo  Tamanio: 
    for %%f in ("dist\GenerarPDFs.exe") do echo    %%~zf bytes
) else (
    echo ERROR: No se genero el ejecutable.
    echo Revisa los mensajes de error arriba.
)

echo.
pause
