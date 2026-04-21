"""
SAUVETAGE - DEFINITION DES NNIVEAUX D'HABILITATION
--------------------------------------------------
Module pour les décorateurs d'autorisation et de permission dans l'application Flask.
Le niveaux d'habilitation est défini par une chaîne de caractères représentant les différentes
permissions d'un utilisateur. Par exemple, "13" signifie que l'utilisateur a les permissions
d'admin (1) et de commercial (3). Les décorateurs permettent de vérifier les permissions
d'un utilisateur avant d'accéder à une route spécifique, en utilisant les constantes définies
dans ce module pour construire la chaîne de permissions requise.
"""

import logging
from functools import wraps
from typing import List, Callable, Any
from flask import abort, g, session, redirect

logger = logging.getLogger("app_front.decorators")

# Définition des niveaux d'habilitation
ADMIN = "1"
COMPTA = "2"
COMMERCIAL = "3"
LOGISTIQUE = "4"
SUPPORT = "5"
INFORMATIQUE = "6"
RH = "7"
DIRECTION = "8"
SUPER_ADMIN = "9"
ALL = [
    ADMIN,
    COMPTA,
    COMMERCIAL,
    LOGISTIQUE,
    SUPPORT,
    INFORMATIQUE,
    RH,
    DIRECTION,
    SUPER_ADMIN,
]


def permission_required(
    permission: List[str] | str, _and: bool = True
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Décorateur pour vérifier les permissions d'un utilisateur avant d'accéder à une route.

    Args:
        permission (List[str] | str): La permission ou la liste de permissions requises pour
        accéder à la route.
        _and (bool): Indique si toutes les permissions doivent être présentes (_and=True) ou
        si au moins une permission suffit (_and=False).
    Returns:
        function: La fonction décorée qui vérifie les permissions avant d'exécuter la logique
        de la route.
    """

    def decorator(f: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(f)
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            if not session:
                return redirect("/login")
            permissions = session.get("permissions", "")
            g.permited = False
            if isinstance(permission, str):
                g.permited = permission in permissions
            else:
                if _and:
                    g.permited = all(p in permissions for p in permission)
                else:
                    g.permited = any(p in permissions for p in permission)
            if not g.permited:
                log = (
                    f"Accès refusé pour l'utilisateur {session.get('username', 'inconnu')} "
                    f"avec les permissions {permissions} "
                    f"pour accéder à la route {f.__name__} "
                    f"qui nécessite les permissions {permission}."
                )
                logger.warning(
                    log, extra={
                        "action": "access_denied",
                        "user_id": session.get("username")
                    }
                )
                abort(
                    403,
                    description="Vous n'êtes pas habilité à accéder à cette ressource.",
                )
            return f(*args, **kwargs)

        return wrapped

    return decorator
