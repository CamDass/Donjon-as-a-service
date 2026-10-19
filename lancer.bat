@echo off
rem Lance l'API : cree l'environnement virtuel si besoin, installe les dependances, demarre le serveur.
rem Double-cliquer sur ce fichier suffit (pas besoin d'activer l'environnement).
cd /d "%~dp0"

".venv\Scripts\python.exe" --version >nul 2>&1
if errorlevel 1 (
    echo [1/3] Creation de l'environnement virtuel...
    if exist ".venv" rmdir /s /q ".venv"
    python -m venv .venv 2>nul || py -3 -m venv .venv
    if errorlevel 1 (
        echo ERREUR : Python est introuvable. Installe Python 3.10 ou plus : https://www.python.org/downloads/
        pause
        exit /b 1
    )
)

echo [2/3] Verification des dependances...
".venv\Scripts\python.exe" -m pip install -q -r requirements.txt
if errorlevel 1 (
    echo ERREUR pendant l'installation des dependances.
    pause
    exit /b 1
)

echo [3/3] Demarrage de l'API sur http://127.0.0.1:8000  (docs : http://127.0.0.1:8000/docs)
echo Arreter le serveur : Ctrl+C
".venv\Scripts\python.exe" -m fastapi dev app/main.py
pause
