"""Utilitaires lies aux metadonnees de requete."""

from typing import Any

from flask import Request


def get_client_ip(req: Request) -> str | None:
    """Retourne l'IP cliente la plus fiable disponible pour les logs."""
    access_route = [ip.strip() for ip in req.access_route if ip and ip.strip()]
    if access_route:
        return access_route[0]

    forwarded_for = req.headers.get("X-Forwarded-For", "")
    if forwarded_for:
        return forwarded_for.split(",", maxsplit=1)[0].strip()

    real_ip = req.headers.get("X-Real-IP", "")
    if real_ip:
        return real_ip.strip()

    return req.remote_addr


def get_request_log_metadata(req: Request) -> dict[str, Any]:
    """Construit des metadonnees reseau ciblees pour le diagnostic des logs."""
    access_route = [ip.strip() for ip in req.access_route if ip and ip.strip()]
    forwarded_for = req.headers.get("X-Forwarded-For")
    real_ip = req.headers.get("X-Real-IP")
    return {
        "client_ip": get_client_ip(req),
        "remote_addr": req.remote_addr,
        "access_route": access_route,
        "x_forwarded_for": forwarded_for,
        "x_real_ip": real_ip,
    }
