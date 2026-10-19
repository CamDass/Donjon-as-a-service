"""Création et consultation des héros."""

from sqlmodel import Session

from app.domain.heros import construire_heros
from app.models.hero import Hero
from app.models.player import Player
from app.schemas.hero import HeroCreate, HeroRead
from app.services.dungeon_map import START_ROOM
from app.services.errors import erreur


def creer_hero(session: Session, donnees: HeroCreate, player: Player) -> Hero:
    metier = construire_heros(
        donnees.classe, donnees.force, donnees.agilite, donnees.intelligence
    )
    hero = Hero(
        nom=donnees.nom,
        classe=donnees.classe,
        force=donnees.force,
        agilite=donnees.agilite,
        intelligence=donnees.intelligence,
        pv=metier.pv_max,
        pv_max=metier.pv_max,
        salle_actuelle=START_ROOM,
        owner_id=player.id,
    )
    session.add(hero)
    session.commit()
    session.refresh(hero)
    return hero


def lister_heros(session: Session, player: Player) -> list[Hero]:
    return session.query(Hero).filter_by(owner_id=player.id).all()


def trouver_hero(session: Session, hero_id: int, player: Player) -> Hero:
    """Renvoie le héros, ou 404 s'il n'existe pas, ou 403 s'il appartient à un autre joueur."""
    hero = session.get(Hero, hero_id)
    if hero is None:
        raise erreur(404, "HERO_NOT_FOUND", f"Le héros {hero_id} n'existe pas.")
    if hero.owner_id != player.id:
        raise erreur(403, "NOT_YOUR_HERO", "Ce héros appartient à un autre joueur.")
    return hero


def vers_hero_read(hero: Hero) -> HeroRead:
    """Convertit le héros stocké en réponse : monstre_pv et owner_id ne sortent pas."""
    return HeroRead(
        id=hero.id,
        nom=hero.nom,
        classe=hero.classe,
        force=hero.force,
        agilite=hero.agilite,
        intelligence=hero.intelligence,
        pv=hero.pv,
        pv_max=hero.pv_max,
        salle_actuelle=hero.salle_actuelle,
        or_=hero.or_,
        victoire=hero.victoire,
        en_combat=hero.monstre_pv is not None,
        est_vivant=hero.pv > 0,
    )
