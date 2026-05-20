@echo off
setlocal
cd /d "%~dp0"

echo === DropShare Windows Build ===
echo.

where python >nul 2>&1
if errorlevel 1 (
    echo Fehler: Python nicht gefunden.
    echo Bitte Python 3.11+ von https://python.org installieren.
    pause & exit /b 1
)

echo Installiere Abhaengigkeiten...
pip install -q PyQt6 aiohttp miniupnpc zeroconf pyinstaller
if errorlevel 1 (
    echo Fehler beim Installieren der Abhaengigkeiten.
    pause & exit /b 1
)

echo.
echo Baue DropShare.exe ...
pyinstaller dropshare.spec --noconfirm --clean
if errorlevel 1 (
    echo Fehler beim Bauen!
    pause & exit /b 1
)

echo.
if exist "dist\DropShare.exe" (
    echo  Fertig^^!  DropShare.exe liegt in dist\
    echo  Die .exe kann beliebig verschoben und per Doppelklick gestartet werden.
    explorer dist
) else (
    echo  DropShare.exe nicht gefunden - Build fehlgeschlagen.
)

pause
