"""Utilitaires lies aux metadonnees de requete."""

import ipaddress
import re
from typing import Any

from flask import Request


def _clean_ip(value: str) -> str:
    """Nettoie une valeur d'IP en retirant un éventuel port et en conservant la partie IP."""
    candidate = value.strip().strip("[]")
    if ":" in candidate and candidate.count(":") == 1:
        host, port = candidate.rsplit(":", 1)
        if port.isdigit():
            return host
    return candidate


def _is_private_ip(value: str) -> bool:
    """Vérifie si une adresse IP appartient aux plages privées locales."""
    try:
        return ipaddress.ip_address(value).is_private
    except ValueError:
        return False


def _select_best_ip(values: list[str]) -> str | None:
    """Choisit la première adresse non privée dans une liste si possible."""
    cleaned_values = [_clean_ip(value) for value in values if value]
    for value in cleaned_values:
        if value and not _is_private_ip(value):
            return value
    for value in cleaned_values:
        if value:
            return value
    return None


def _extract_forwarded_values(req: Request) -> list[str]:
    """Extrait les adresses IP depuis les en-têtes de proxy standard et non standard."""
    values: list[str] = []

    x_forwarded_for = req.headers.get("X-Forwarded-For", "")
    if x_forwarded_for:
        values.extend(
            item.strip() for item in x_forwarded_for.split(",") if item and item.strip()
        )

    forwarded_header = req.headers.get("Forwarded", "")
    if forwarded_header:
        for element in forwarded_header.split(","):
            match = re.search(r"(?:^|;)for=(?:\"([^\"]+)\"|([^;]+))", element)
            if not match:
                continue
            candidate = (match.group(1) or match.group(2) or "").strip()
            if candidate and candidate.lower() != "unknown":
                values.append(candidate)

    return values


def get_client_ip(req: Request) -> str | None:
    """Retourne l'IP cliente la plus fiable disponible pour les logs."""
    forwarded_values = _extract_forwarded_values(req)
    if forwarded_values:
        selected = _select_best_ip(forwarded_values)
        if selected:
            return selected

    for header_name in ("CF-Connecting-IP", "True-Client-IP", "X-Real-IP"):
        header_value = req.headers.get(header_name, "")
        if header_value:
            values = [item.strip() for item in header_value.split(",") if item and item.strip()]
            selected = _select_best_ip(values)
            if selected:
                return selected

    access_route = [ip.strip() for ip in req.access_route if ip and ip.strip()]
    if access_route:
        return _select_best_ip(access_route) or access_route[0]

    # Fallback: si le middleware ProxyFix a déjà résolu un client réel, l'utiliser.
    if req.remote_addr and req.remote_addr != "127.0.0.1" and req.remote_addr != "0.0.0.0":
        return req.remote_addr

    return req.remote_addr


def get_request_log_metadata(req: Request) -> dict[str, Any]:
    """Construit des metadonnees reseau ciblees pour le diagnostic des logs."""
    forwarded_for = req.headers.get("X-Forwarded-For")
    real_ip = req.headers.get("X-Real-IP")
    cf_connecting_ip = req.headers.get("CF-Connecting-IP")
    true_client_ip = req.headers.get("True-Client-IP")
    forwarded_header = req.headers.get("Forwarded")

    forwarded_values = _extract_forwarded_values(req)
    access_route = [ip.strip() for ip in req.access_route if ip and ip.strip()]
    if forwarded_values:
        access_route = forwarded_values + access_route

    return {
        "client_ip": get_client_ip(req),
        "remote_addr": req.remote_addr,
        "access_route": access_route,
        "x_forwarded_for": forwarded_for,
        "x_real_ip": real_ip,
        "forwarded": forwarded_header,
        "cf_connecting_ip": cf_connecting_ip,
        "true_client_ip": true_client_ip,
        "proxy_fix_remote_addr": getattr(req, "remote_addr", None),
    }
