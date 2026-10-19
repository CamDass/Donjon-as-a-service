"""La carte du client : positions des salles et brouillard."""

from client import play


def test_positions_des_salles():
    positions = play.placer_salles(play.charger_carte())
    assert positions["entree"] == (0, 0)
    assert positions["hall"] == (0, 1)
    assert positions["bibliotheque"] == (-1, 1)  # à l'ouest du hall
    assert positions["crypte"] == (1, 1)  # à l'est du hall
    assert positions["salle_trone"] == (0, 4)
    assert len(set(positions.values())) == len(positions)  # aucune salle n'en recouvre une autre


def test_brouillard_au_depart():
    texte = "\n".join(play.dessiner_carte(play.charger_carte(), set(), "entree"))
    assert "[@]" in texte and "[?]" in texte
    assert "Grand hall" not in texte and "Salle du trône" not in texte  # pas encore visités


def test_salles_visitees_apparaissent():
    texte = "\n".join(play.dessiner_carte(play.charger_carte(), {"entree", "hall"}, "hall"))
    assert "[1] Entrée du donjon" in texte
    assert "[@] Grand hall effondré" in texte
    assert "Crypte" not in texte  # voisine du hall mais pas visitée


def test_carte_complete_sans_inexplore():
    carte = play.charger_carte()
    texte = "\n".join(play.dessiner_carte(carte, set(carte["rooms"]), "salle_trone"))
    assert "[?]" not in texte
