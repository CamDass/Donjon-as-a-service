"""Classement public."""

from typing import Literal

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.database import get_session
from app.schemas.leaderboard import LeaderboardEntry
from app.services import leaderboard_service

router = APIRouter(prefix="/leaderboard", tags=["Classement"])


@router.get("", response_model=list[LeaderboardEntry])
def classement(
    classe: Literal["guerrier", "mage", "voleur"] | None = None,
    session: Session = Depends(get_session),
):
    """Les 10 meilleurs héros (vainqueurs d'abord, puis par or). Filtre optionnel par classe."""
    return leaderboard_service.classement(session, classe)
