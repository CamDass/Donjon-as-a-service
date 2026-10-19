"""Classement des héros."""

from sqlmodel import Session

from app.models.hero import Hero
from app.models.player import Player
from app.schemas.leaderboard import LeaderboardEntry


def classement(session: Session, classe: str | None = None) -> list[LeaderboardEntry]:
    """Les 10 meilleurs héros : vainqueurs d'abord, puis par quantité d'or."""
    requete = session.query(Hero, Player).join(Player, Hero.owner_id == Player.id)
    if classe is not None:
        requete = requete.filter(Hero.classe == classe)
    lignes = requete.order_by(Hero.victoire.desc(), Hero.or_.desc(), Hero.id).limit(10).all()

    resultat = []
    for rang, (hero, player) in enumerate(lignes, start=1):
        resultat.append(
            LeaderboardEntry(
                rang=rang,
                nom=hero.nom,
                classe=hero.classe,
                joueur=player.username,
                or_=hero.or_,
                victoire=hero.victoire,
                est_vivant=hero.pv > 0,
                salle=hero.salle_actuelle,
            )
        )
    return resultat
