"""Schémas des salles et des déplacements."""

from typing import Literal

from pydantic import BaseModel


class MonstreRead(BaseModel):
    nom: str
    pv: int
    pv_max: int
    attaque: int


class RoomRead(BaseModel):
    id: str
    nom: str
    description: str
    sorties: list[str]
    monstre: MonstreRead | None = None  # présent seulement si un combat est en cours


class MoveRequest(BaseModel):
    direction: Literal["nord", "sud", "est", "ouest"]
