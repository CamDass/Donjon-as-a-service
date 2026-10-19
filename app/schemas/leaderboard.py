"""Schéma d'une ligne du classement."""

from pydantic import BaseModel


class LeaderboardEntry(BaseModel):
    rang: int
    nom: str
    classe: str
    joueur: str
    or_: int
    victoire: bool
    est_vivant: bool
    salle: str
