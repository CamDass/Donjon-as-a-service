"""Règles du jeu : testées sans FastAPI ni base de données."""

import pytest

from app.domain.heros import Guerrier, Heros, Mage, Voleur, construire_heros


def test_heros_est_abstrait():
    with pytest.raises(TypeError):
        Heros(2, 2, 6)


def test_exemples_du_sujet():
    assert Guerrier(6, 2, 2).calculer_degats() == (14, False)
    assert Guerrier(6, 2, 2).pv_max == 32
    assert Mage(2, 2, 6).calculer_degats() == (19, False)
    assert Mage(2, 2, 6).pv_max == 24
    assert Voleur(2, 6, 2).calculer_degats() == (14, False)
    assert Voleur(2, 6, 2).pv_max == 24


def test_voleur_critique_un_coup_sur_trois():
    resultats = [Voleur(2, 6, 2, nb_attaques=n).calculer_degats() for n in range(6)]
    assert resultats == [(14, False), (14, False), (28, True)] * 2


def test_armure_du_guerrier():
    assert Guerrier(6, 2, 2).subir_degats(7) == 6
    assert Guerrier(6, 2, 2).subir_degats(1) == 1  # jamais moins de 1
    assert Mage(2, 2, 6).subir_degats(7) == 7  # pas d'armure


def test_fabrique_sans_condition_sur_la_classe():
    assert isinstance(construire_heros("guerrier", 6, 2, 2), Guerrier)
    assert isinstance(construire_heros("mage", 2, 2, 6), Mage)
    assert isinstance(construire_heros("voleur", 2, 6, 2), Voleur)
