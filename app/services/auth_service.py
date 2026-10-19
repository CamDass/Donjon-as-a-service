"""Comptes joueurs : inscription, connexion, jeton JWT."""

import os
from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash
from sqlmodel import Session

from app.models.player import Player
from app.services.errors import erreur

# La clé vient de l'environnement ; la valeur par défaut ne sert qu'en développement
SECRET_KEY = os.getenv("SECRET_KEY", "cle-de-developpement-a-changer-en-production")
ALGORITHM = "HS256"
DUREE_TOKEN_MINUTES = 60

mot_de_passe = PasswordHash.recommended()


def inscrire(session: Session, username: str, password: str) -> Player:
    if session.query(Player).filter_by(username=username).first() is not None:
        raise erreur(409, "USERNAME_TAKEN", "Ce nom d'utilisateur est déjà pris.")
    player = Player(username=username, hashed_password=mot_de_passe.hash(password))
    session.add(player)
    session.commit()
    session.refresh(player)
    return player


def connecter(session: Session, username: str, password: str) -> str:
    """Vérifie les identifiants et renvoie un jeton JWT."""
    player = session.query(Player).filter_by(username=username).first()
    # Même message pour « utilisateur inconnu » et « mot de passe faux »
    if player is None or not mot_de_passe.verify(password, player.hashed_password):
        raise erreur(401, "INVALID_CREDENTIALS", "Nom d'utilisateur ou mot de passe incorrect.")
    expiration = datetime.now(timezone.utc) + timedelta(minutes=DUREE_TOKEN_MINUTES)
    return jwt.encode({"sub": player.username, "exp": expiration}, SECRET_KEY, algorithm=ALGORITHM)


def joueur_du_token(session: Session, token: str) -> Player:
    """Décode le jeton et renvoie le joueur correspondant, sinon 401."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        raise erreur(401, "INVALID_TOKEN", "Jeton invalide ou expiré.")
    player = session.query(Player).filter_by(username=payload["sub"]).first()
    if player is None:
        raise erreur(401, "INVALID_TOKEN", "Jeton invalide ou expiré.")
    return player
