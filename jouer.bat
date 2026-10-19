@echo off
rem Lance le client terminal (le serveur doit deja tourner : voir lancer.bat).
rem Sans argument : mode interactif. Avec arguments : jouer.bat look --hero 1
cd /d "%~dp0"
if "%~1"=="" (
    ".venv\Scripts\python.exe" client\play.py play
    pause
) else (
    ".venv\Scripts\python.exe" client\play.py %*
)
