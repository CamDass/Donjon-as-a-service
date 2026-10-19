# Donjon-as-a-service

Jeu de rôle textuel piloté par une API FastAPI : héros, donjon, combats et authentification JWT,
jouable depuis le terminal. Projet du module Python Backend & FastAPI.

## Installation (à faire une seule fois)

Prérequis : Python 3.10 ou plus récent (`python --version`).

```bash
# 1. Créer et activer un environnement virtuel
python -m venv .venv
# Windows (PowerShell) :
.venv\Scripts\Activate.ps1
# macOS / Linux :
source .venv/bin/activate

# 2. Installer les dépendances
pip install -r requirements.txt
```

## Démarrage rapide (Windows)

Double-cliquer sur **`lancer.bat`** : il crée l'environnement virtuel au besoin, installe les
dépendances et démarre l'API (http://127.0.0.1:8000/docs). Ensuite **`jouer.bat`** ouvre le client
terminal. Rien à activer à la main.

> « fastapi introuvable » / « No module named sqlmodel » : le Python utilisé n'est pas celui de
> `.venv`. Causes fréquentes : `Activate.ps1` bloqué par PowerShell (politique d'exécution), bouton
> « Run » d'un éditeur configuré sur un autre interpréteur, ou `python app/main.py` au lieu de
> `fastapi dev app/main.py`. `lancer.bat` appelle directement le Python de `.venv` et évite tout ça.

## Lancer l'API

Depuis la racine du projet (le dossier qui contient `app/`) :

```bash
fastapi dev app/main.py
```

Ouvrez ensuite http://127.0.0.1:8000/docs : la route `GET /health` doit répondre
`{"status": "ok", ...}`. Si c'est le cas, vous êtes prêts.

## Structure

```
app/
  main.py              point d'entrée, branchement des routers
  database.py          connexion SQLite (FOURNI)
  models/              tables SQLModel
  schemas/             schémas Pydantic d'entrée et de sortie
  domain/              classes métier (Heros, Guerrier, Mage, Voleur)
  services/            logique du jeu
    dungeon_map.py     lecture de la carte (FOURNI)
  routes/              routers FastAPI
data/dungeon_map.json  carte du donjon (FOURNI, ne pas modifier)
client/play.py         client terminal (BONUS)
```

## Réinitialiser la partie

Arrêtez le serveur et supprimez le fichier `dungeon.db` : il sera recréé au prochain lancement.
À faire aussi si vous ajoutez une colonne à une table (SQLite ne met pas à jour une table existante).

---

## Jouer depuis le terminal

Serveur lancé dans un terminal, client dans un autre :

```bash
python client/play.py play          # mode interactif (inscription, choix du héros, jeu)
python client/play.py --help        # une commande par action
```

## Lancer les tests

```bash
pytest
```


## Notre rendu

- **Membres du groupe :** camille victor gabriel
- **Lien du dépôt Git :** https://github.com/CamDass/Donjon-as-a-service
- **Palier atteint :** 4 (le héros, le donjon, le combat, le verrou)
- **Bonus réalisés :** B-1 client terminal (`python client/play.py play`), B-2 classement
  (`GET /leaderboard`), B-3 tests (`pytest`), B-5 journalisation (console du serveur)
- **Ce qui ne fonctionne pas / difficultés :** L’activation de l’environnement virtuel était bloquée par PowerShell, ce qui faisait échouer le lancement (fastapi introuvable), et la règle « somme des stats = 10 » a demandé un model_validator Pydantic pour renvoyer une 422 au lieu d’une 400.
