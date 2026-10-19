"""Règles du jeu des héros : aucune dépendance à FastAPI ni à la base de données."""

from abc import ABC, abstractmethod


class Heros(ABC):
    """Héros abstrait : porte les statistiques et les règles communes."""

    def __init__(self, force: int, agilite: int, intelligence: int, nb_attaques: int = 0):
        self.force = force
        self.agilite = agilite
        self.intelligence = intelligence
        # Nombre de coups déjà portés : sert au coup critique du voleur
        self.nb_attaques = nb_attaques

    @property
    def pv_max(self) -> int:
        return 20 + self.force * 2

    @abstractmethod
    def calculer_degats(self) -> tuple[int, bool]:
        """Renvoie (dégâts infligés, coup critique ?)."""

    def subir_degats(self, attaque_monstre: int) -> int:
        """Renvoie les dégâts réellement subis. Par défaut : l'attaque du monstre."""
        return attaque_monstre


class Guerrier(Heros):
    def calculer_degats(self) -> tuple[int, bool]:
        return 2 + self.force * 2, False

    def subir_degats(self, attaque_monstre: int) -> int:
        # Armure : -1 dégât, mais au moins 1
        return max(1, attaque_monstre - 1)


class Mage(Heros):
    def calculer_degats(self) -> tuple[int, bool]:
        return 1 + self.intelligence * 3, False


class Voleur(Heros):
    def calculer_degats(self) -> tuple[int, bool]:
        degats = 2 + self.agilite * 2
        # Un coup sur trois est critique : le 3e, le 6e, le 9e...
        critique = (self.nb_attaques + 1) % 3 == 0
        if critique:
            degats = degats * 2
        return degats, critique


CLASSES = {"guerrier": Guerrier, "mage": Mage, "voleur": Voleur}


def construire_heros(
    classe: str, force: int, agilite: int, intelligence: int, nb_attaques: int = 0
) -> Heros:
    """Fabrique l'objet métier d'une classe, sans aucun `if` sur le nom de la classe."""
    return CLASSES[classe](force, agilite, intelligence, nb_attaques)
