"""Routes d'authentification."""

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session

from app.database import get_session
from app.schemas.auth import PlayerCreate, PlayerRead, Token
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Authentification"])


@router.post("/register", response_model=PlayerRead, status_code=201)
def register(donnees: PlayerCreate, session: Session = Depends(get_session)):
    """Crée un compte joueur."""
    return auth_service.inscrire(session, donnees.username, donnees.password)


@router.post("/login", response_model=Token)
def login(
    formulaire: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session),
):
    """Se connecte (formulaire OAuth2) et reçoit un jeton JWT."""
    token = auth_service.connecter(session, formulaire.username, formulaire.password)
    return {"access_token": token, "token_type": "bearer"}
