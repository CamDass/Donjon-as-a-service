"""Table des héros."""

from sqlmodel import Field, SQLModel


class Hero(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    nom: str
    classe: str
    force: int
    agilite: int
    intelligence: int
    pv: int
    pv_max: int
    salle_actuelle: str
    or_: int = 0
    monstre_pv: int | None = None  # None : aucun combat en cours
    victoire: bool = False  # vrai quand la Liche est vaincue
    nb_attaques: int = 0  # sert au coup critique du voleur
    owner_id: int = Field(foreign_key="player.id")
