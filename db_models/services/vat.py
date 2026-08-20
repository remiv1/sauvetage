"""Règles métier partagées pour l'historique des taux de TVA."""

from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from db_models.objects.vat import VatRate


def close_superseded_vat_rates(
    session: Session,
    code: int,
    effective_at: datetime,
    excluded_id: int | None = None,
) -> Sequence[VatRate]:
    """Clôture les taux d'un code remplacés à la prise d'effet d'un nouveau taux.

    La borne de fin est exclusive : un taux fermé à `effective_at` reste applicable
    jusqu'à l'instant précédant le nouveau taux.
    """
    if effective_at.tzinfo is None:
        effective_at = effective_at.replace(tzinfo=timezone.utc)
    stmt = select(VatRate).where(
        VatRate.code == code,
        VatRate.date_start < effective_at,
        or_(VatRate.date_end.is_(None), VatRate.date_end > effective_at),
    )
    if excluded_id is not None:
        stmt = stmt.where(VatRate.id != excluded_id)
    superseded_rates = session.execute(stmt).scalars().all()
    for rate in superseded_rates:
        rate.date_end = effective_at
    return superseded_rates
