"""Schémas de l'authentification."""

from pydantic import BaseModel, Field


class PlayerCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=20)
    password: str = Field(..., min_length=6)


class PlayerRead(BaseModel):
    id: int
    username: str


class Token(BaseModel):
    access_token: str
    token_type: str
