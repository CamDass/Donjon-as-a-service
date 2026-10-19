"""Le jeu : description des salles, déplacement, combat et repos."""

import asyncio
import logging

from sqlmodel import Session

from app.domain.heros import construire_heros
from app.models.hero import Hero
from app.schemas.combat import AttackResult
from app.schemas.room import MonstreRead, RoomRead
from app.services.dungeon_map import FINAL_ROOM, get_monster_of_room, get_room
from app.services.errors import erreur

journal = logging.getLogger("dungeon")

DUREE_REPOS = 3  # secondes


def verifier_vivant(hero: Hero) -> None:
    if hero.pv <= 0:
        raise erreur(409, "HERO_DEAD", f"{hero.nom} est mort : il ne peut plus agir.")


def verifier_hors_combat(hero: Hero) -> None:
    if hero.monstre_pv is not None:
        raise erreur(409, "IN_COMBAT", f"{hero.nom} est en plein combat.")


def decrire_salle(hero: Hero) -> RoomRead:
    salle = get_room(hero.salle_actuelle)
    monstre = None
    if hero.monstre_pv is not None:
        modele = get_monster_of_room(hero.salle_actuelle)
        monstre = MonstreRead(
            nom=modele["name"],
            pv=hero.monstre_pv,
            pv_max=modele["hp"],
            attaque=modele["attack"],
        )
    return RoomRead(
        id=hero.salle_actuelle,
        nom=salle["name"],
        description=salle["description"],
        sorties=list(salle["exits"].keys()),
        monstre=monstre,
    )


def deplacer(session: Session, hero: Hero, direction: str) -> RoomRead:
    verifier_vivant(hero)
    verifier_hors_combat(hero)
    sorties = get_room(hero.salle_actuelle)["exits"]
    if direction not in sorties:
        raise erreur(400, "NO_EXIT", f"Il n'y a pas de passage vers le {direction}.")

    hero.salle_actuelle = sorties[direction]
    monstre = get_monster_of_room(hero.salle_actuelle)
    if monstre is not None:
        # Le donjon est maudit : le monstre réapparaît à chaque entrée
        hero.monstre_pv = monstre["hp"]
    session.commit()
    session.refresh(hero)

    salle = get_room(hero.salle_actuelle)
    journal.info("%s va vers le %s et entre dans : %s", hero.nom, direction, salle["name"])
    if monstre is not None:
        journal.info("%s : %s apparait (%d PV)", salle["name"], monstre["name"], monstre["hp"])
    return decrire_salle(hero)


def attaquer(session: Session, hero: Hero) -> AttackResult:
    verifier_vivant(hero)
    if hero.monstre_pv is None:
        raise erreur(409, "NO_MONSTER", "Il n'y a aucun monstre à attaquer ici.")

    monstre = get_monster_of_room(hero.salle_actuelle)
    metier = construire_heros(
        hero.classe, hero.force, hero.agilite, hero.intelligence, hero.nb_attaques
    )

    # Le héros frappe en premier
    degats, critique = metier.calculer_degats()
    hero.nb_attaques += 1
    hero.monstre_pv = max(0, hero.monstre_pv - degats)
    pv_monstre = hero.monstre_pv
    degats_subis = 0
    or_gagne = 0

    if pv_monstre == 0:
        issue = "monstre_vaincu"
        or_gagne = monstre["gold"]
        hero.or_ += or_gagne
        hero.monstre_pv = None
        if hero.salle_actuelle == FINAL_ROOM:
            hero.victoire = True
    else:
        # Le monstre survit : il riposte
        degats_subis = metier.subir_degats(monstre["attack"])
        hero.pv = max(0, hero.pv - degats_subis)
        issue = "heros_mort" if hero.pv == 0 else "en_cours"

    session.commit()
    session.refresh(hero)

    journal.info(
        "%s frappe %s : %d degats%s | riposte : %d | PV heros %d/%d, PV monstre %d",
        hero.nom, monstre["name"], degats, " (CRITIQUE)" if critique else "",
        degats_subis, hero.pv, hero.pv_max, pv_monstre,
    )
    if issue == "monstre_vaincu":
        journal.info("%s vainc %s et gagne %d or", hero.nom, monstre["name"], or_gagne)
    if issue == "heros_mort":
        journal.warning("%s est tombe face a %s", hero.nom, monstre["name"])
    if hero.victoire:
        journal.info("%s a vaincu %s : le donjon est libere !", hero.nom, monstre["name"])

    return AttackResult(
        degats_infliges=degats,
        critique=critique,
        degats_subis=degats_subis,
        pv_heros=hero.pv,
        pv_monstre=pv_monstre,
        issue=issue,
        or_gagne=or_gagne,
        victoire=hero.victoire,
    )


async def se_reposer(session: Session, hero: Hero) -> Hero:
    verifier_vivant(hero)
    verifier_hors_combat(hero)
    journal.info("%s se repose...", hero.nom)

    # await : le serveur répond aux autres requêtes pendant l'attente
    await asyncio.sleep(DUREE_REPOS)

    # Le héros a pu changer pendant l'attente : on relit la base et on revérifie
    session.refresh(hero)
    verifier_vivant(hero)
    verifier_hors_combat(hero)
    hero.pv = hero.pv_max
    session.commit()
    session.refresh(hero)
    journal.info("%s est repose : %d/%d PV", hero.nom, hero.pv, hero.pv_max)
    return hero
