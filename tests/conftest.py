"""Outils de test : base SQLite en mémoire, utilisée à la place de dungeon.db."""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.database import get_session
from app.main import app
from app.services import game_service

moteur_test = create_engine(
    "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
)


def session_de_test():
    with Session(moteur_test) as session:
        yield session


@pytest.fixture(autouse=True)
def base_propre(monkeypatch):
    """Base vide pour chaque test, et repos instantané."""
    SQLModel.metadata.drop_all(moteur_test)
    SQLModel.metadata.create_all(moteur_test)
    app.dependency_overrides[get_session] = session_de_test
    monkeypatch.setattr(game_service, "DUREE_REPOS", 0)
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def client():
    # Pas de « with » : on ne lance pas le démarrage, qui toucherait à dungeon.db
    return TestClient(app)


def creer_joueur(client, username="alice"):
    """Crée un compte, se connecte, et renvoie les en-têtes d'authentification."""
    client.post("/auth/register", json={"username": username, "password": "secret123"})
    reponse = client.post("/auth/login", data={"username": username, "password": "secret123"})
    return {"Authorization": f"Bearer {reponse.json()['access_token']}"}


def creer_hero(client, entetes, classe="guerrier", force=6, agilite=2, intelligence=2):
    reponse = client.post(
        "/heroes",
        headers=entetes,
        json={
            "nom": "Aragorn",
            "classe": classe,
            "force": force,
            "agilite": agilite,
            "intelligence": intelligence,
        },
    )
    return reponse.json()


def modifier_hero(hero_id, **champs):
    """Modifie directement un héros en base (pour préparer un cas de test)."""
    from app.models.hero import Hero

    with Session(moteur_test) as session:
        hero = session.get(Hero, hero_id)
        for nom, valeur in champs.items():
            setattr(hero, nom, valeur)
        session.commit()
