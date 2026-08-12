"""Charge le registre partagé des types de logs et des modules associés."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import toml

_CONFIG_PATH = Path(__file__).resolve().with_name("log_categories.toml")


def load_log_registry() -> dict[str, Any]:
    """Charge le registre TOML des types de logs et des modules associés."""
    with _CONFIG_PATH.open("r", encoding="utf-8") as handle:
        return toml.load(handle)


def get_default_log_type() -> str:
    """Retourne le type de log par défaut."""
    config = load_log_registry()
    return str(config.get("default", "logs"))


def get_log_types() -> list[str]:
    """Retourne l'ordre des types de log défini dans la configuration."""
    config = load_log_registry()
    types: list[str] = []
    for key, value in config.items():
        if key == "default":
            continue
        if isinstance(value, dict):
            types.append(key)
    return types


def get_group_modules(log_type: str) -> list[str]:
    """Retourne les modules associés à un type de log donné."""
    config = load_log_registry()
    group = config.get(log_type, {})
    modules = group.get("modules", []) if isinstance(group, dict) else []
    return [str(module) for module in modules]


def resolve_log_type(module_name: str | None) -> str:
    """Détermine le type de log associé à un module, sinon retourne le défaut."""
    candidate = (module_name or "").strip()
    if not candidate:
        return get_default_log_type()

    for log_type in get_log_types():
        if candidate in get_group_modules(log_type):
            return log_type

    return get_default_log_type()
