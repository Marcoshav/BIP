@echo off
chcp 65001 >nul
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (set PY=py -3) else (set PY=python)
%PY% --version >nul 2>nul
if errorlevel 1 (
    echo No encontre Python. Instalalo desde https://www.python.org/downloads/ ^(marca "Add Python to PATH"^).
    pause
    exit /b 1
)
%PY% -m pip install --upgrade --quiet --disable-pip-version-check -r requirements.txt pyinstaller
%PY% -m pip install --upgrade --quiet --disable-pip-version-check -r requirements-medios.txt
%PY% -m PyInstaller --noconfirm --onefile --windowed --name Bip --hidden-import PyQt6.QtMultimedia --collect-all winrt bip.py
if not exist dist\Bip.exe (
    echo Fallo con winrt, reintentando sin el lector de portadas...
    %PY% -m PyInstaller --noconfirm --onefile --windowed --name Bip --hidden-import PyQt6.QtMultimedia bip.py
)
if exist dist\Bip.exe (
    copy /y dist\Bip.exe Bip.exe >nul
    echo.
    echo Listo! Se creo Bip.exe en esta carpeta. Hacele doble clic.
) else (
    echo Algo fallo al crear el exe.
)
pause
