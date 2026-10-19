"""Dépendances partagées par les routes."""

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session

from app.database import get_session
from app.models.hero import Hero
from app.models.player import Player
from app.services import auth_service, hero_service

# tokenUrl : la route de connexion, utilisée par le bouton « Authorize » de Swagger
oauth2 = OAuth2PasswordBearer(tokenUrl="auth/login")


def get_current_player(
    token: str = Depends(oauth2), session: Session = Depends(get_session)
) -> Player:
    return auth_service.joueur_du_token(session, token)


def get_hero(
    hero_id: int,
    session: Session = Depends(get_session),
    player: Player = Depends(get_current_player),
) -> Hero:
    """Récupère le héros de l'URL : 404 s'il n'existe pas, 403 s'il n'est pas à ce joueur."""
    return hero_service.trouver_hero(session, hero_id, player)
