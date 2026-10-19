"""Tests de l'API : un cas nominal et les cas d'erreur de chaque palier."""

import asyncio

import httpx
import pytest
from sqlmodel import Session

from app.main import app
from app.models.player import Player
from app.services import game_service
from tests.conftest import creer_hero, creer_joueur, modifier_hero, moteur_test


def detail(reponse):
    return reponse.json()["detail"]


# ---------- Palier 1 : le héros ----------


def test_creation_hero(client):
    entetes = creer_joueur(client)
    reponse = client.post(
        "/heroes",
        headers=entetes,
        json={"nom": "Aragorn", "classe": "guerrier", "force": 6, "agilite": 2, "intelligence": 2},
    )
    assert reponse.status_code == 201
    hero = reponse.json()
    assert hero["salle_actuelle"] == "entree"
    assert hero["pv"] == hero["pv_max"] == 32
    assert hero["or_"] == 0
    assert hero["en_combat"] is False and hero["est_vivant"] is True
    # Les champs internes ne sortent pas
    assert "monstre_pv" not in hero and "owner_id" not in hero


@pytest.mark.parametrize(
    "corps",
    [
        {"nom": "Aragorn", "classe": "guerrier", "force": 8, "agilite": 4, "intelligence": 3},
        {"nom": "Aragorn", "classe": "paladin", "force": 6, "agilite": 2, "intelligence": 2},
        {"nom": "Ar", "classe": "mage", "force": 6, "agilite": 2, "intelligence": 2},
        {"nom": "Aragorn", "classe": "mage", "force": 9, "agilite": 1, "intelligence": 0},
    ],
    ids=["somme-15", "classe-inconnue", "nom-trop-court", "stats-hors-limites"],
)
def test_creation_invalide_renvoie_422(client, corps):
    entetes = creer_joueur(client)
    assert client.post("/heroes", headers=entetes, json=corps).status_code == 422


def test_hero_inconnu_404_au_format_impose(client):
    entetes = creer_joueur(client)
    reponse = client.get("/heroes/9999", headers=entetes)
    assert reponse.status_code == 404
    assert detail(reponse)["error"] == "HERO_NOT_FOUND"
    assert "message" in detail(reponse)


# ---------- Palier 2 : le donjon ----------


def test_deplacement_et_salle(client):
    entetes = creer_joueur(client)
    hero = creer_hero(client, entetes)
    salle = client.get(f"/heroes/{hero['id']}/room", headers=entetes).json()
    assert salle["id"] == "entree" and salle["sorties"] == ["nord"] and salle["monstre"] is None

    reponse = client.post(f"/heroes/{hero['id']}/move", headers=entetes, json={"direction": "nord"})
    assert reponse.status_code == 200
    assert reponse.json()["id"] == "hall"


def test_direction_sans_sortie_400_et_direction_inconnue_422(client):
    entetes = creer_joueur(client)
    hero = creer_hero(client, entetes)
    url = f"/heroes/{hero['id']}/move"
    sans_sortie = client.post(url, headers=entetes, json={"direction": "sud"})
    assert sans_sortie.status_code == 400
    assert detail(sans_sortie)["error"] == "NO_EXIT"
    assert client.post(url, headers=entetes, json={"direction": "haut"}).status_code == 422


def test_salle_hantee_declenche_un_combat(client):
    entetes = creer_joueur(client)
    hero = creer_hero(client, entetes)
    url = f"/heroes/{hero['id']}"
    client.post(f"{url}/move", headers=entetes, json={"direction": "nord"})
    salle = client.post(f"{url}/move", headers=entetes, json={"direction": "ouest"}).json()
    assert salle["monstre"]["nom"] == "Gobelin"
    assert salle["monstre"]["pv"] == salle["monstre"]["pv_max"] == 12


# ---------- Palier 3 : le combat ----------


def aller_a_la_bibliotheque(client, entetes, hero):
    url = f"/heroes/{hero['id']}"
    client.post(f"{url}/move", headers=entetes, json={"direction": "nord"})
    client.post(f"{url}/move", headers=entetes, json={"direction": "ouest"})
    return url


def test_combat_contre_le_gobelin(client):
    entetes = creer_joueur(client)
    hero = creer_hero(client, entetes)  # guerrier : 14 dégâts, le gobelin a 12 PV
    url = aller_a_la_bibliotheque(client, entetes, hero)

    tour = client.post(f"{url}/attack", headers=entetes).json()
    assert tour["issue"] == "monstre_vaincu"
    assert tour["degats_infliges"] == 14 and tour["degats_subis"] == 0
    assert tour["or_gagne"] == 10 and tour["victoire"] is False
    assert client.get(url, headers=entetes).json()["or_"] == 10


def test_riposte_du_monstre(client):
    entetes = creer_joueur(client)
    hero = creer_hero(client, entetes, "voleur", force=2, agilite=2, intelligence=6)  # 6 dégâts
    url = aller_a_la_bibliotheque(client, entetes, hero)

    tour = client.post(f"{url}/attack", headers=entetes).json()
    assert tour["issue"] == "en_cours"
    assert tour["pv_monstre"] == 6 and tour["degats_subis"] == 3
    assert tour["pv_heros"] == 24 - 3


def test_etats_incoherents_409(client):
    entetes = creer_joueur(client)
    hero = creer_hero(client, entetes)
    url = f"/heroes/{hero['id']}"

    sans_monstre = client.post(f"{url}/attack", headers=entetes)
    assert sans_monstre.status_code == 409 and detail(sans_monstre)["error"] == "NO_MONSTER"

    client.post(f"{url}/move", headers=entetes, json={"direction": "nord"})
    client.post(f"{url}/move", headers=entetes, json={"direction": "ouest"})
    fuite = client.post(f"{url}/move", headers=entetes, json={"direction": "est"})
    assert fuite.status_code == 409 and detail(fuite)["error"] == "IN_COMBAT"
    repos = client.post(f"{url}/rest", headers=entetes)
    assert repos.status_code == 409 and detail(repos)["error"] == "IN_COMBAT"


def test_heros_mort_reste_consultable(client):
    entetes = creer_joueur(client)
    hero = creer_hero(client, entetes)
    url = f"/heroes/{hero['id']}"
    modifier_hero(hero["id"], pv=0)

    for chemin in ["/move", "/attack", "/rest"]:
        reponse = client.post(f"{url}{chemin}", headers=entetes, json={"direction": "nord"})
        assert reponse.status_code == 409 and detail(reponse)["error"] == "HERO_DEAD"

    assert client.get(url, headers=entetes).json()["est_vivant"] is False
    assert client.get(f"{url}/room", headers=entetes).status_code == 200


def test_repos_restaure_les_pv(client):
    entetes = creer_joueur(client)
    hero = creer_hero(client, entetes)
    modifier_hero(hero["id"], pv=5)
    reponse = client.post(f"/heroes/{hero['id']}/rest", headers=entetes)
    assert reponse.status_code == 200 and reponse.json()["pv"] == 32


@pytest.mark.parametrize(
    "classe, force, agilite, intelligence",
    [("guerrier", 6, 2, 2), ("mage", 2, 2, 6), ("voleur", 2, 6, 2)],
)
def test_chaque_classe_peut_vaincre_la_liche(client, classe, force, agilite, intelligence):
    entetes = creer_joueur(client)
    hero = creer_hero(client, entetes, classe, force, agilite, intelligence)
    url = f"/heroes/{hero['id']}"
    dernier_tour = None

    # entree -> hall -> couloir (rat) -> antichambre (ogre) -> salle du trône (liche)
    for _ in range(4):
        client.post(f"{url}/move", headers=entetes, json={"direction": "nord"})
        while client.get(f"{url}/room", headers=entetes).json()["monstre"] is not None:
            dernier_tour = client.post(f"{url}/attack", headers=entetes).json()
        client.post(f"{url}/rest", headers=entetes)  # un repos après chaque salle

    assert dernier_tour["issue"] == "monstre_vaincu"
    assert dernier_tour["victoire"] is True
    assert client.get(url, headers=entetes).json()["victoire"] is True


@pytest.mark.anyio
async def test_le_repos_ne_bloque_pas_le_serveur(monkeypatch):
    monkeypatch.setattr(game_service, "DUREE_REPOS", 0.5)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        identifiants = {"username": "alice", "password": "secret123"}
        await client.post("/auth/register", json=identifiants)
        token = (await client.post("/auth/login", data=identifiants)).json()["access_token"]
        entetes = {"Authorization": f"Bearer {token}"}
        corps = {"nom": "Aragorn", "classe": "guerrier", "force": 6, "agilite": 2, "intelligence": 2}
        hero = (await client.post("/heroes", headers=entetes, json=corps)).json()

        repos = asyncio.create_task(client.post(f"/heroes/{hero['id']}/rest", headers=entetes))
        await asyncio.sleep(0.1)
        sante = await client.get("/health")
        assert sante.status_code == 200
        assert not repos.done()  # /health a répondu pendant que le repos était en cours
        assert (await repos).status_code == 200


# ---------- Palier 4 : le verrou ----------


def test_sans_token_401(client):
    assert client.get("/heroes").status_code == 401
    assert client.get("/heroes", headers={"Authorization": "Bearer faux"}).status_code == 401


def test_inscription_connexion_et_mot_de_passe_hache(client):
    identifiants = {"username": "alice", "password": "secret123"}
    assert client.post("/auth/register", json=identifiants).status_code == 201
    doublon = client.post("/auth/register", json=identifiants)
    assert doublon.status_code == 409 and detail(doublon)["error"] == "USERNAME_TAKEN"
    faux = client.post("/auth/login", data={"username": "alice", "password": "mauvais"})
    assert faux.status_code == 401

    with Session(moteur_test) as session:
        assert session.query(Player).first().hashed_password != "secret123"


def test_heros_d_un_autre_joueur_403(client):
    alice = creer_joueur(client, "alice")
    bob = creer_joueur(client, "bobby")
    hero = creer_hero(client, alice)
    reponse = client.post(f"/heroes/{hero['id']}/move", headers=bob, json={"direction": "nord"})
    assert reponse.status_code == 403 and detail(reponse)["error"] == "NOT_YOUR_HERO"
    assert client.get("/heroes", headers=bob).json() == []
    assert len(client.get("/heroes", headers=alice).json()) == 1


# ---------- Bonus : classement ----------


def test_classement_public_et_trie(client):
    alice = creer_joueur(client, "alice")
    bob = creer_joueur(client, "bobby")
    riche = creer_hero(client, alice)
    vainqueur = creer_hero(client, bob, "mage", 2, 2, 6)
    modifier_hero(riche["id"], or_=500)
    modifier_hero(vainqueur["id"], or_=10, victoire=True)

    lignes = client.get("/leaderboard").json()  # pas de token
    assert [ligne["rang"] for ligne in lignes] == [1, 2]
    assert lignes[0]["victoire"] is True and lignes[0]["joueur"] == "bobby"
    assert lignes[1]["or_"] == 500
    assert [ligne["classe"] for ligne in client.get("/leaderboard?classe=mage").json()] == ["mage"]
    assert client.get("/leaderboard?classe=paladin").status_code == 422
