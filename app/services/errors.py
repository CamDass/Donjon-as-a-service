"""Fabrique des erreurs métier au format imposé :
{"detail": {"error": "CODE", "message": "..."}}
"""

from fastapi import HTTPException


def erreur(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"error": code, "message": message})
