@echo off
chcp 65001 >nul
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
    py -3 -m pip install --quiet --disable-pip-version-check -r requirements.txt
    py -3 -m pip install --quiet --disable-pip-version-check -r requirements-medios.txt
    start "" pyw -3 bip.py
    exit /b 0
)
where python >nul 2>nul
if %errorlevel%==0 (
    python -m pip install --quiet --disable-pip-version-check -r requirements.txt
    python -m pip install --quiet --disable-pip-version-check -r requirements-medios.txt
    start "" pythonw bip.py
    exit /b 0
)
echo No encontre Python. Instalalo desde https://www.python.org/downloads/
echo (marca la casilla "Add Python to PATH") y volve a abrir este archivo.
pause
