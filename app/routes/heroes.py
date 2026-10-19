"""Routes des héros : création, consultation, déplacement, combat, repos."""

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.database import get_session
from app.models.hero import Hero
from app.models.player import Player
from app.routes.dependencies import get_current_player, get_hero
from app.schemas.combat import AttackResult
from app.schemas.hero import HeroCreate, HeroRead
from app.schemas.room import MoveRequest, RoomRead
from app.services import game_service, hero_service

router = APIRouter(prefix="/heroes", tags=["Héros"])


@router.post("", response_model=HeroRead, status_code=201)
def creer_hero(
    donnees: HeroCreate,
    session: Session = Depends(get_session),
    player: Player = Depends(get_current_player),
):
    """Crée un héros dans la salle de départ, avec ses points de vie au maximum."""
    hero = hero_service.creer_hero(session, donnees, player)
    return hero_service.vers_hero_read(hero)


@router.get("", response_model=list[HeroRead])
def lister_heros(
    session: Session = Depends(get_session),
    player: Player = Depends(get_current_player),
):
    """Liste les héros du joueur connecté."""
    heros = hero_service.lister_heros(session, player)
    return [hero_service.vers_hero_read(h) for h in heros]


@router.get("/{hero_id}", response_model=HeroRead)
def lire_hero(hero: Hero = Depends(get_hero)):
    """Consulte un héros (même mort)."""
    return hero_service.vers_hero_read(hero)


@router.get("/{hero_id}/room", response_model=RoomRead, tags=["Jeu"])
def decrire_salle(hero: Hero = Depends(get_hero)):
    """Décrit la salle où se trouve le héros."""
    return game_service.decrire_salle(hero)


@router.post("/{hero_id}/move", response_model=RoomRead, tags=["Jeu"])
def deplacer(
    mouvement: MoveRequest,
    hero: Hero = Depends(get_hero),
    session: Session = Depends(get_session),
):
    """Déplace le héros dans une direction et renvoie la nouvelle salle."""
    return game_service.deplacer(session, hero, mouvement.direction)


@router.post("/{hero_id}/attack", response_model=AttackResult, tags=["Jeu"])
def attaquer(
    hero: Hero = Depends(get_hero),
    session: Session = Depends(get_session),
):
    """Déroule un tour de combat : le héros frappe, puis le monstre riposte s'il survit."""
    return game_service.attaquer(session, hero)


@router.post("/{hero_id}/rest", response_model=HeroRead, tags=["Jeu"])
async def se_reposer(
    hero: Hero = Depends(get_hero),
    session: Session = Depends(get_session),
):
    """Repos de 3 secondes (asynchrone) : le héros récupère tous ses points de vie."""
    hero = await game_service.se_reposer(session, hero)
    return hero_service.vers_hero_read(hero)
