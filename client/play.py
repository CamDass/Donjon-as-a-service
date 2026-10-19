"""BONUS — Client terminal de « Dungeon as a Service : L'Emprise du Cocker ».

Une commande par action :
    python client/play.py register --username alice --password secret
    python client/play.py login --username alice --password secret
    python client/play.py create --nom Aragorn --classe guerrier --force 6 --agilite 2 --intelligence 2
    python client/play.py heroes
    python client/play.py look --hero 1
    python client/play.py move --hero 1 --direction nord
    python client/play.py attack --hero 1
    python client/play.py rest --hero 1
    python client/play.py leaderboard --classe mage

Ou, pour jouer en continu :
    python client/play.py play

Le jeton JWT reçu au login est enregistré dans le fichier .token (à la racine du projet).
L'adresse de l'API peut être changée avec la variable d'environnement DUNGEON_API_URL.
"""

import argparse
import getpass
import json
import os
import random
import sys
from pathlib import Path

import requests

API_URL = os.getenv("DUNGEON_API_URL", "http://127.0.0.1:8000")
TOKEN_FILE = Path(__file__).resolve().parent.parent / ".token"

# ---------------------------------------------------------------------------
# Affichage
# ---------------------------------------------------------------------------

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass
if os.name == "nt":
    os.system("")  # active les couleurs ANSI dans le terminal Windows

CODES_COULEUR = {"rouge": "31", "vert": "32", "jaune": "33", "violet": "35", "cyan": "36", "gris": "90"}
AVEC_COULEURS = sys.stdout.isatty() and "NO_COLOR" not in os.environ


def couleur(texte: str, nom: str) -> str:
    if not AVEC_COULEURS:
        return texte
    return f"\033[{CODES_COULEUR[nom]}m{texte}\033[0m"


def dire(texte: str = "", nom_couleur: str | None = None) -> None:
    print(couleur(texte, nom_couleur) if nom_couleur else texte)


# ---------------------------------------------------------------------------
# L'histoire : les monstres de l'API deviennent les habitants du monastère
# ---------------------------------------------------------------------------

REVEIL = (
    "Tu ouvres les yeux sur une voûte de pierre. Un chant lointain, répété par des milliers de\n"
    "voix : « Ou-af... Ou-af... ». Tu ne sais pas où tu es. Tu sais seulement que tu dois sortir\n"
    "de l'emprise du cocker qui règne sur ce monastère."
)

VICTOIRE = (
    "Tu frappes une dernière fois. La petite couronne tombe et roule sur les dalles. Victor Wilson\n"
    "cligne des yeux, s'assoit, puis remue la queue : ce n'est plus qu'un chien. Partout dans le\n"
    "monastère, le chant s'arrête. Des milliers de moines se réveillent, perdus. Au fond de la\n"
    "salle du trône, une porte s'ouvre sur la lumière du jour."
)

MORT = (
    "Tu tombes à genoux. Les grands yeux du cocker sont la dernière chose que tu vois. Ton corps\n"
    "rejoint la procession des moines, et ton esprit erre dans les couloirs. Ton nom reste gravé\n"
    "au Hall des Légendes, parmi les fantômes."
)

REPOS = "Tu t'assois sur un banc de prière. Le chant te berce sans t'emporter..."

AUTRE_MOINE = "Un autre moine a pris la place du précédent. Ils sont des milliers."

# Clé : nom du monstre dans l'API (data/dungeon_map.json, qu'on ne modifie pas)
PERSONNAGES = {
    "Rat géant": {
        "nom": "Le rat du cellier",
        "cible": "le rat du cellier",
        "entree": "Quelque chose de gras détale entre les sacs de grain... puis se retourne vers toi.",
        "riposte": "Le rat te mord le mollet : {degats} dégâts.",
    },
    "Gobelin": {
        "nom": "Le novice",
        "cible": "le novice",
        "entree": "Un enfant moine lève les yeux de son livre. Il le referme. Lentement.",
        "riposte": "Le novice t'assène un grimoire relié cuir : {degats} dégâts.",
    },
    "Squelette": {
        "nom": "La statue de moine",
        "cible": "la statue de moine",
        "entree": "Une statue de moine fait grincer sa nuque de pierre dans ta direction.",
        "riposte": "Un poing de pierre s'abat sur toi : {degats} dégâts.",
    },
    "Ogre": {
        "nom": "Frère Colosse",
        "cible": "Frère Colosse",
        "entree": "Une ombre immense bloque le passage. L'encensoir se balance. Frère Colosse ne dit rien.",
        "riposte": "L'encensoir te percute dans un nuage de fumée : {degats} dégâts.",
    },
    "La Liche": {
        "nom": "Victor Wilson",
        "cible": "Victor Wilson",
        "entree": "Sur un trône trop grand pour lui, un petit cocker te regarde. Sa couronne brille. "
        "Tes genoux tremblent.",
        "riposte": "Victor Wilson te fixe de ses grands yeux humides. Ta volonté vacille : "
        "{degats} dégâts.",
    },
}

COUPS = {
    "guerrier": [
        "Ton épée frappe {cible} : {degats} dégâts.",
        "Ta lame s'abat sur {cible} : {degats} dégâts.",
    ],
    "mage": [
        "Une flamme jaillit de tes doigts et enveloppe {cible} : {degats} dégâts.",
        "Un éclair claque et frappe {cible} : {degats} dégâts.",
    ],
    "voleur": [
        "Tu frappes {cible} au défaut de sa robe : {degats} dégâts.",
        "Ta dague se plante dans {cible} : {degats} dégâts.",
    ],
}
COUP_CRITIQUE_VOLEUR = (
    "Tu disparais dans l'ombre d'un pilier... et reparais dans son dos. "
    "COUP CRITIQUE : {degats} dégâts !"
)

ERREURS_RACONTEES = {
    "NO_EXIT": "Un mur. Rien qu'un mur, couvert de prières gravées.",
    "NO_MONSTER": "Tu frappes le vide. Seul l'écho du chant te répond.",
    "HERO_DEAD": "Tu n'es plus qu'un fantôme. Les vivants ne t'entendent plus.",
    "NOT_YOUR_HERO": "Ce héros n'est pas le tien.",
}


def personnage(nom_monstre: str) -> dict:
    return PERSONNAGES.get(
        nom_monstre,
        {"nom": nom_monstre, "cible": nom_monstre, "entree": f"{nom_monstre} surgit !",
         "riposte": nom_monstre + " te frappe : {degats} dégâts."},
    )


# ---------------------------------------------------------------------------
# Dialogue avec l'API
# ---------------------------------------------------------------------------


class ErreurJeu(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def lire_token() -> str | None:
    if TOKEN_FILE.exists():
        return TOKEN_FILE.read_text(encoding="utf-8").strip() or None
    return None


def lire_erreur(reponse: requests.Response) -> ErreurJeu:
    try:
        detail = reponse.json().get("detail")
    except ValueError:
        return ErreurJeu("HTTP_ERROR", f"Erreur {reponse.status_code}")
    if isinstance(detail, dict):
        return ErreurJeu(detail.get("error", "ERROR"), detail.get("message", ""))
    if isinstance(detail, list):  # 422 : liste d'erreurs Pydantic
        lignes = []
        for e in detail:
            champ = ".".join(str(p) for p in e["loc"][1:])
            message = e["msg"].removeprefix("Value error, ")
            lignes.append(f"{champ} : {message}" if champ else message)
        return ErreurJeu("VALIDATION", " ; ".join(lignes))
    if reponse.status_code == 401:
        return ErreurJeu("NOT_LOGGED", "Tu n'es pas connecté : utilise d'abord la commande login.")
    return ErreurJeu("HTTP_ERROR", str(detail))


def appeler(methode: str, chemin: str, **options):
    entetes = {}
    token = lire_token()
    if token:
        entetes["Authorization"] = f"Bearer {token}"
    try:
        reponse = requests.request(
            methode, API_URL + chemin, headers=entetes, timeout=15, **options
        )
    except requests.exceptions.ConnectionError:
        raise ErreurJeu("NO_SERVER", f"Impossible de joindre l'API sur {API_URL}. Le serveur est-il lancé ?")
    if reponse.status_code >= 400:
        raise lire_erreur(reponse)
    return reponse.json()


def se_connecter(username: str, password: str) -> None:
    jeton = appeler("POST", "/auth/login", data={"username": username, "password": password})
    TOKEN_FILE.write_text(jeton["access_token"], encoding="utf-8")


def raconter_erreur(erreur: ErreurJeu, monstre: str | None = None) -> str:
    if erreur.code == "IN_COMBAT":
        cible = personnage(monstre)["nom"] if monstre else "Un ennemi"
        return f"{cible} te barre la route. Impossible de fuir."
    return ERREURS_RACONTEES.get(erreur.code, erreur.message)


# ---------------------------------------------------------------------------
# Affichage des réponses de l'API
# ---------------------------------------------------------------------------


def afficher_heros(hero: dict) -> None:
    etat = "en vie" if hero["est_vivant"] else "fantôme"
    dire(f"{hero['nom']} ({hero['classe']}) - héros n°{hero['id']}", "cyan")
    dire(f"  PV {hero['pv']}/{hero['pv_max']}   offrandes : {hero['or_']}   état : {etat}")
    dire(f"  force {hero['force']}, agilité {hero['agilite']}, intelligence {hero['intelligence']}")
    dire(f"  salle : {hero['salle_actuelle']}" + ("   (en combat)" if hero["en_combat"] else ""))
    if hero["victoire"]:
        dire("  Tu as brisé l'emprise du cocker.", "jaune")


def afficher_salle(salle: dict, deja_vue_avec_monstre: bool = False) -> None:
    dire()
    dire(salle["nom"], "jaune")
    dire(salle["description"])
    dire("Sorties : " + ", ".join(salle["sorties"]))
    monstre = salle["monstre"]
    if monstre is not None:
        perso = personnage(monstre["nom"])
        dire()
        if deja_vue_avec_monstre:
            dire(AUTRE_MOINE, "gris")
        dire(perso["entree"], "rouge")
        dire(f"{perso['nom']} : PV {monstre['pv']}/{monstre['pv_max']}", "rouge")


def raconter_tour(tour: dict, classe: str, monstre: dict) -> None:
    perso = personnage(monstre["nom"])
    if tour["critique"] and classe == "voleur":
        phrase = COUP_CRITIQUE_VOLEUR
    else:
        phrase = random.choice(COUPS[classe])
    dire(phrase.format(cible=perso["cible"], degats=tour["degats_infliges"]), "cyan")

    if tour["issue"] == "monstre_vaincu":
        dire(f"{perso['nom']} s'effondre. Tu ramasses {tour['or_gagne']} pièces d'offrande.", "jaune")
        return
    dire(perso["riposte"].format(degats=tour["degats_subis"]), "rouge")
    if classe == "guerrier" and tour["degats_subis"] < monstre["attaque"]:
        dire("Ton armure encaisse une partie du choc.", "gris")
    dire(f"Toi : PV {tour['pv_heros']}   {perso['nom']} : PV {tour['pv_monstre']}/{monstre['pv_max']}")


def afficher_classement(lignes: list) -> None:
    dire("=== HALL DES LEGENDES ===", "jaune")
    if not lignes:
        dire("Personne n'est encore passé par ici.")
        return
    dire(f"{'#':>2}  {'HEROS':<20} {'CLASSE':<9} {'JOUEUR':<20} {'OR':>5}  ETAT")
    for ligne in lignes:
        if ligne["victoire"]:
            etat, nom_couleur = "[LIBRE]", "jaune"
        elif not ligne["est_vivant"]:
            etat, nom_couleur = "[FANTOME]", "gris"
        else:
            etat, nom_couleur = "en vie", None
        texte = (f"{ligne['rang']:>2}  {ligne['nom']:<20} {ligne['classe']:<9} "
                 f"{ligne['joueur']:<20} {ligne['or_']:>5}  {etat}")
        dire(texte, nom_couleur)


# ---------------------------------------------------------------------------
# Actions (communes aux commandes et au mode interactif)
# ---------------------------------------------------------------------------


def action_regarder(hero_id: int) -> dict:
    salle = appeler("GET", f"/heroes/{hero_id}/room")
    noter_salle(hero_id, salle["id"])
    afficher_salle(salle)
    return salle


def action_deplacer(hero_id: int, direction: str, deja_battus: set | None = None) -> dict:
    salle = appeler("POST", f"/heroes/{hero_id}/move", json={"direction": direction})
    noter_salle(hero_id, salle["id"])
    revenant = deja_battus is not None and salle["id"] in deja_battus
    afficher_salle(salle, deja_vue_avec_monstre=revenant)
    return salle


def action_attaquer(hero_id: int, classe: str, monstre: dict | None) -> dict:
    """Frappe le monstre ; `monstre` est celui de la dernière description de salle."""
    if monstre is None:
        monstre = appeler("GET", f"/heroes/{hero_id}/room")["monstre"]
    tour = appeler("POST", f"/heroes/{hero_id}/attack")
    raconter_tour(tour, classe, monstre)
    if tour["issue"] == "heros_mort":
        dire()
        dire(MORT, "rouge")
    if tour["victoire"]:
        dire()
        dire(VICTOIRE, "jaune")
    return tour


def action_reposer(hero_id: int) -> dict:
    dire(REPOS, "gris")
    sys.stdout.flush()
    hero = appeler("POST", f"/heroes/{hero_id}/rest")
    dire(f"Tes forces reviennent : PV {hero['pv']}/{hero['pv_max']}.", "vert")
    return hero


# ---------------------------------------------------------------------------
# Commandes
# ---------------------------------------------------------------------------


def cmd_health(args) -> None:
    dire(appeler("GET", "/health")["message"])


def cmd_register(args) -> None:
    mot_de_passe = args.password or getpass.getpass("Mot de passe : ")
    joueur = appeler("POST", "/auth/register", json={"username": args.username, "password": mot_de_passe})
    dire(f"Compte « {joueur['username']} » créé. Connecte-toi avec la commande login.", "vert")


def cmd_login(args) -> None:
    mot_de_passe = args.password or getpass.getpass("Mot de passe : ")
    se_connecter(args.username, mot_de_passe)
    dire(f"Bienvenue, {args.username}. Jeton enregistré dans {TOKEN_FILE.name}.", "vert")


def cmd_create(args) -> None:
    corps = {"nom": args.nom, "classe": args.classe, "force": args.force,
             "agilite": args.agilite, "intelligence": args.intelligence}
    hero = appeler("POST", "/heroes", json=corps)
    oublier_carte(hero["id"])
    dire(REVEIL)
    dire()
    afficher_heros(hero)


def cmd_heroes(args) -> None:
    heros = appeler("GET", "/heroes")
    if not heros:
        dire("Tu n'as encore aucun héros : utilise la commande create.")
    for hero in heros:
        afficher_heros(hero)
        dire()


def cmd_look(args) -> None:
    action_regarder(args.hero)


def cmd_move(args) -> None:
    action_deplacer(args.hero, args.direction)


def cmd_attack(args) -> None:
    hero = appeler("GET", f"/heroes/{args.hero}")
    action_attaquer(args.hero, hero["classe"], None)


def cmd_rest(args) -> None:
    action_reposer(args.hero)


def cmd_leaderboard(args) -> None:
    parametres = {"classe": args.classe} if args.classe else {}
    afficher_classement(appeler("GET", "/leaderboard", params=parametres))


# ---------------------------------------------------------------------------
# La carte : on ne voit que les salles déjà visitées (brouillard)
# ---------------------------------------------------------------------------

CARTE_JSON = Path(__file__).resolve().parent.parent / "data" / "dungeon_map.json"
VECTEURS = {"nord": (0, 1), "sud": (0, -1), "est": (1, 0), "ouest": (-1, 0)}
PAS_X = 6  # largeur d'une case [x] (3) + largeur d'un couloir horizontal (3)


def charger_carte() -> dict:
    with CARTE_JSON.open(encoding="utf-8") as f:
        return json.load(f)


def placer_salles(carte: dict) -> dict[str, tuple[int, int]]:
    """Calcule la position (x, y) de chaque salle en suivant les sorties depuis l'entrée."""
    positions = {carte["start_room"]: (0, 0)}
    a_voir = [carte["start_room"]]
    while a_voir:
        salle = a_voir.pop(0)
        x, y = positions[salle]
        for direction, cible in carte["rooms"][salle]["exits"].items():
            if cible not in positions:
                dx, dy = VECTEURS[direction]
                positions[cible] = (x + dx, y + dy)
                a_voir.append(cible)
    return positions


def fichier_memoire(hero_id: int) -> Path:
    return TOKEN_FILE.parent / f".carte_{hero_id}.json"


def salles_visitees(hero_id: int) -> set[str]:
    try:
        return set(json.loads(fichier_memoire(hero_id).read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return set()


def noter_salle(hero_id: int, salle_id: str) -> None:
    visitees = salles_visitees(hero_id)
    if salle_id not in visitees:
        visitees.add(salle_id)
        try:
            fichier_memoire(hero_id).write_text(json.dumps(sorted(visitees)), encoding="utf-8")
        except OSError:
            pass  # la carte est un confort : on ne plante jamais pour elle


def oublier_carte(hero_id: int) -> None:
    try:
        fichier_memoire(hero_id).unlink()
    except OSError:
        pass


def dessiner_carte(carte: dict, visitees: set[str], salle_id: str) -> list[str]:
    """Renvoie les lignes de la carte : [@] toi, [n] visitée, [?] sortie pas encore explorée."""
    positions = placer_salles(carte)
    numeros = {identifiant: n for n, identifiant in enumerate(carte["rooms"], start=1)}
    visitees = visitees | {salle_id}
    connues = set(visitees)
    for identifiant in visitees:
        connues.update(carte["rooms"][identifiant]["exits"].values())

    x_min = min(positions[i][0] for i in connues)
    y_max = max(positions[i][1] for i in connues)
    largeur = (max(positions[i][0] for i in connues) - x_min) * PAS_X + 3
    hauteur = (y_max - min(positions[i][1] for i in connues)) * 2 + 1
    grille = [[" "] * largeur for _ in range(hauteur)]

    def ecrire(ligne: int, colonne: int, texte: str) -> None:
        for i, caractere in enumerate(texte):
            grille[ligne][colonne + i] = caractere

    def case(identifiant: str) -> tuple[int, int]:
        x, y = positions[identifiant]
        return (y_max - y) * 2, (x - x_min) * PAS_X

    for identifiant in connues:
        ligne, colonne = case(identifiant)
        if identifiant == salle_id:
            marque = "@"
        elif identifiant in visitees:
            marque = str(numeros[identifiant])
        else:
            marque = "?"
        ecrire(ligne, colonne, f"[{marque}]")

    for identifiant in visitees:  # les couloirs partent des salles visitées
        ligne, colonne = case(identifiant)
        for direction in carte["rooms"][identifiant]["exits"]:
            if direction == "est":
                ecrire(ligne, colonne + 3, "---")
            elif direction == "ouest":
                ecrire(ligne, colonne - 3, "---")
            elif direction == "nord":
                ecrire(ligne - 1, colonne + 1, "|")
            elif direction == "sud":
                ecrire(ligne + 1, colonne + 1, "|")

    lignes = ["".join(ligne).rstrip() for ligne in grille]
    lignes.append("")
    for identifiant in sorted(visitees, key=lambda i: numeros[i]):
        nom = carte["rooms"][identifiant]["name"]
        etiquette = "@" if identifiant == salle_id else str(numeros[identifiant])
        lignes.append(f"[{etiquette}] {nom}" + ("   <- tu es ici" if identifiant == salle_id else ""))
    if connues - visitees:
        lignes.append("[?] sortie pas encore explorée")
    return lignes


def afficher_carte(hero_id: int, salle_id: str) -> None:
    dire()
    dire("Carte du monastère (seuls tes pas sont connus)", "jaune")
    dire()
    for ligne in dessiner_carte(charger_carte(), salles_visitees(hero_id), salle_id):
        dire(ligne, "jaune" if ligne.startswith("[@]") else None)


def cmd_map(args) -> None:
    salle = appeler("GET", f"/heroes/{args.hero}/room")
    noter_salle(args.hero, salle["id"])
    afficher_carte(args.hero, salle["id"])


# ---------------------------------------------------------------------------
# Mode interactif : python client/play.py play
# ---------------------------------------------------------------------------

AIDE = """Commandes (écris le mot, ou sa première lettre) :
  nord / sud / est / ouest   te déplacer (n, s, e, o)
  frapper (f)                un tour de combat
  repos (r)                  tous tes PV en 3 secondes (impossible en combat)
  voir (v)                   redécrire la salle
  carte (k)                  la carte des salles que tu as visitées
  moi (m)                    ta fiche : PV, offrandes, statistiques
  top (t)                    le Hall des Légendes (« top mage » : une seule classe)
  aide (?)                   cette liste
  quitter (q)                sortir du jeu"""

COMMENT_JOUER = (
    "Comment jouer : avance de salle en salle vers le nord pour atteindre la salle du trône.\n"
    "Quand un ennemi apparaît, tape « frapper » jusqu'à ce qu'il tombe. Blessé ? Tape « repos ».\n"
    "Perdu ? Tape « carte » (ou k) pour voir les salles déjà visitées."
)

# Les anciens noms restent acceptés
ALIAS = {
    "n": "nord", "s": "sud", "e": "est", "o": "ouest", "w": "ouest",
    "f": "frapper", "a": "frapper", "attaquer": "frapper", "attaque": "frapper", "attack": "frapper",
    "r": "repos", "dormir": "repos", "reposer": "repos", "rest": "repos",
    "v": "voir", "regarder": "voir", "look": "voir", "l": "voir",
    "k": "carte", "map": "carte",
    "m": "moi", "heros": "moi", "stats": "moi",
    "t": "top", "classement": "top", "c": "top",
    "?": "aide", "h": "aide", "help": "aide",
    "q": "quitter", "quit": "quitter", "exit": "quitter",
}
DIRECTIONS = ("nord", "sud", "est", "ouest")


def demander(invite: str) -> str:
    try:
        return input(invite).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        dire("À bientôt.", "gris")
        sys.exit(0)


def demander_nombre(invite: str) -> int:
    while True:
        texte = demander(invite)
        if texte.isdigit():
            return int(texte)
        dire("Entre un nombre entier.", "rouge")


def s_identifier() -> None:
    """Réutilise le jeton enregistré s'il est encore valable, sinon connexion ou inscription."""
    if lire_token():
        try:
            appeler("GET", "/heroes")
            return
        except ErreurJeu as e:
            if e.code == "NO_SERVER":
                raise
    while True:
        choix = demander("[c]onnexion ou [i]nscription ? ").lower()
        if choix not in ("c", "i"):
            continue
        username = demander("Nom d'utilisateur : ")
        mot_de_passe = getpass.getpass("Mot de passe : ")
        try:
            if choix == "i":
                appeler("POST", "/auth/register", json={"username": username, "password": mot_de_passe})
            se_connecter(username, mot_de_passe)
            return
        except ErreurJeu as e:
            if e.code == "NO_SERVER":
                raise
            dire(e.message, "rouge")


def creer_heros_interactif() -> dict:
    dire("Choisis ton héros. Les trois statistiques (de 1 à 8) doivent totaliser 10.")
    while True:
        nom = demander("Nom (3 à 20 caractères) : ")
        classe = demander("Classe (guerrier / mage / voleur) : ").lower()
        force = demander_nombre("Force : ")
        agilite = demander_nombre("Agilité : ")
        intelligence = demander_nombre("Intelligence : ")
        corps = {"nom": nom, "classe": classe, "force": force,
                 "agilite": agilite, "intelligence": intelligence}
        try:
            hero = appeler("POST", "/heroes", json=corps)
            oublier_carte(hero["id"])
            return hero
        except ErreurJeu as e:
            if e.code == "NO_SERVER":
                raise
            dire(e.message, "rouge")


def choisir_heros() -> dict:
    while True:
        heros = appeler("GET", "/heroes")
        if not heros:
            return creer_heros_interactif()
        dire()
        for numero, hero in enumerate(heros, start=1):
            etat = "" if hero["est_vivant"] else " (fantôme)"
            dire(f"  {numero}. {hero['nom']} - {hero['classe']} - PV {hero['pv']}/{hero['pv_max']}{etat}")
        dire("  n. nouveau héros")
        choix = demander("Ton choix : ").lower()
        if choix == "n":
            return creer_heros_interactif()
        if choix.isdigit() and 1 <= int(choix) <= len(heros):
            hero = heros[int(choix) - 1]
            if hero["est_vivant"]:
                return hero
            dire(raconter_erreur(ErreurJeu("HERO_DEAD", "")), "gris")


def afficher_choix(salle: dict, hero: dict) -> None:
    """Rappelle au joueur ce qu'il peut faire maintenant."""
    dire()
    if salle["monstre"] is not None:
        dire("Que faire ?  frapper", "jaune")
        dire("(combat en cours : impossible de fuir ou de se reposer)   autres : carte  moi  aide", "gris")
        return
    dire("Que faire ?  aller vers : " + "  ".join(salle["sorties"]), "jaune")
    blesse = hero["pv"] <= hero["pv_max"] * 0.4
    conseil = "  <- tu es blessé !" if blesse else ""
    dire(f"autres : repos{conseil}  voir  carte  moi  top  aide", "gris")


def lire_commande(hero: dict) -> tuple[str, str]:
    invite = f"\n[PV {hero['pv']}/{hero['pv_max']} | offrandes {hero['or_']}] > "
    mots = demander(invite).lower().split()
    if mots and mots[0] in ("aller", "go") and len(mots) > 1:
        mots = mots[1:]  # « aller nord » = « nord »
    if not mots:
        return "", ""
    return ALIAS.get(mots[0], mots[0]), " ".join(mots[1:])


def boucle_de_jeu(hero: dict) -> None:
    """Joue avec un héros jusqu'à sa mort, sa victoire ou un « quitter »."""
    deja_battus: set[str] = set()
    salle = action_regarder(hero["id"])
    dire()
    dire(COMMENT_JOUER, "gris")
    while True:
        hero = appeler("GET", f"/heroes/{hero['id']}")
        afficher_choix(salle, hero)
        commande, argument = lire_commande(hero)
        monstre = salle["monstre"]
        try:
            if commande == "quitter":
                sys.exit(0)
            elif commande == "aide":
                dire(AIDE)
            elif commande == "voir":
                salle = action_regarder(hero["id"])
            elif commande in DIRECTIONS:
                salle = action_deplacer(hero["id"], commande, deja_battus)
            elif commande == "frapper":
                tour = action_attaquer(hero["id"], hero["classe"], monstre)
                salle = appeler("GET", f"/heroes/{hero['id']}/room")
                if tour["issue"] == "monstre_vaincu" and monstre is not None:
                    deja_battus.add(salle["id"])
                if tour["issue"] == "heros_mort" or tour["victoire"]:
                    return
            elif commande == "repos":
                action_reposer(hero["id"])
            elif commande == "carte":
                afficher_carte(hero["id"], salle["id"])
            elif commande == "moi":
                afficher_heros(hero)
            elif commande == "top":
                parametres = {"classe": argument} if argument else {}
                afficher_classement(appeler("GET", "/leaderboard", params=parametres))
            elif commande:
                dire(f"Je ne comprends pas « {commande} ». Tape « aide » pour la liste.", "rouge")
        except ErreurJeu as e:
            if e.code == "NO_SERVER":
                raise
            dire(raconter_erreur(e, monstre["nom"] if monstre else None), "rouge")


def cmd_play(args) -> None:
    dire("DUNGEON AS A SERVICE - L'Emprise du Cocker", "jaune")
    dire()
    dire(REVEIL)
    dire()
    s_identifier()
    while True:
        hero = choisir_heros()
        boucle_de_jeu(hero)
        dire()
        dire("Ta partie est terminée. Tu peux choisir un autre héros.", "gris")


# ---------------------------------------------------------------------------
# Programme principal
# ---------------------------------------------------------------------------


def construire_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Dungeon as a Service — client terminal")
    sous = parser.add_subparsers(dest="command", required=True)

    def commande(nom, aide, fonction, hero=False):
        p = sous.add_parser(nom, help=aide)
        p.set_defaults(fonction=fonction)
        if hero:
            p.add_argument("--hero", type=int, required=True, help="identifiant du héros")
        return p

    commande("health", "Vérifie que l'API répond", cmd_health)
    p = commande("register", "Crée un compte", cmd_register)
    p.add_argument("--username", required=True)
    p.add_argument("--password", help="demandé en saisie masquée si absent")
    p = commande("login", "Se connecte et enregistre le jeton", cmd_login)
    p.add_argument("--username", required=True)
    p.add_argument("--password", help="demandé en saisie masquée si absent")
    p = commande("create", "Crée un héros", cmd_create)
    p.add_argument("--nom", "--name", required=True)
    p.add_argument("--classe", required=True, choices=["guerrier", "mage", "voleur"])
    p.add_argument("--force", type=int, required=True)
    p.add_argument("--agilite", type=int, required=True)
    p.add_argument("--intelligence", type=int, required=True)
    commande("heroes", "Liste tes héros", cmd_heroes)
    commande("look", "Décrit la salle du héros", cmd_look, hero=True)
    p = commande("move", "Déplace le héros", cmd_move, hero=True)
    p.add_argument("--direction", required=True, choices=list(DIRECTIONS))
    commande("attack", "Un tour de combat", cmd_attack, hero=True)
    commande("rest", "Repos de 3 secondes", cmd_rest, hero=True)
    commande("map", "Affiche la carte des salles visitées", cmd_map, hero=True)
    p = commande("leaderboard", "Le Hall des Légendes", cmd_leaderboard)
    p.add_argument("--classe", choices=["guerrier", "mage", "voleur"])
    commande("play", "Mode interactif", cmd_play)
    return parser


def main() -> None:
    args = construire_parser().parse_args()
    try:
        args.fonction(args)
    except ErreurJeu as e:
        dire(raconter_erreur(e), "rouge")
        sys.exit(1)


if __name__ == "__main__":
    main()
