"""Utils pour dashboard."""

from typing import Tuple
from datetime import datetime, timedelta


def define_period(start: datetime, period: str) -> Tuple[datetime, ...]:
    """Définit les bornes d'une période à partir d'une date de début et d'un type de période."""
    if period == "A":  # Annuel
        end = _add_a_year(start)
    elif period == "S":  # Semestriel
        end = _add_a_semester(start)
    elif period == "T":  # Trimestriel
        end = _add_a_trimestre(start)
    elif period == "M":  # Mensuel
        end = _add_a_month(start)
    elif period == "W":  # Hebdomadaire
        end = _add_a_week(start)
    else:
        raise ValueError("Période invalide. Utiliser A, S, T, M ou W.")
    return start, end


def _add_a_year(start: datetime) -> datetime:
    """Ajoute un an à une date."""
    try:
        return datetime(
            year=int(start.year) + 1, month=int(start.month), day=int(start.day)
        ) - timedelta(days=1)
    except ValueError:
        # Cas du 29 février
        return datetime(year=int(start.year) + 1, month=3, day=1) - timedelta(days=1)


def _add_a_semester(start: datetime) -> datetime:
    """Ajoute un semestre à une date."""
    month = int(start.month)
    year = int(start.year)
    if month <= 6:
        return datetime(year=year, month=month + 6, day=int(start.day)) - timedelta(
            days=1
        )
    return datetime(year=year + 1, month=month - 6, day=int(start.day)) - timedelta(
        days=1
    )


def _add_a_trimestre(start: datetime) -> datetime:
    """Ajoute un trimestre à une date."""
    month = int(start.month)
    year = int(start.year)
    if month <= 9:
        return datetime(year=year, month=month + 3, day=int(start.day)) - timedelta(
            days=1
        )
    return datetime(year=year + 1, month=month - 9, day=int(start.day)) - timedelta(
        days=1
    )


def _add_a_month(start: datetime) -> datetime:
    """Ajoute un mois à une date."""
    month = int(start.month)
    year = int(start.year)
    if month == 12:
        return datetime(year=year + 1, month=1, day=int(start.day)) - timedelta(days=1)
    return datetime(year=year, month=month + 1, day=int(start.day)) - timedelta(days=1)


def _add_a_week(start: datetime) -> datetime:
    """Ajoute une semaine à une date."""
    return start + timedelta(days=6)
