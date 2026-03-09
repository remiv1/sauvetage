"""Module de gestion des routages."""

WHITE_LIST_PREFIXES = [
    "/static/",
    "/health",
    "/ready",
    "/user/login",
    "/admin/first-user",
]
WHITE_LIST_SUFFIXES = [
    "/login",
    "/first-user",
    ".css",
    ".js",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".ico",
]


def is_allowed(path: str) -> bool:
    """Vérifie si le chemin demandé est dans la liste blanche."""
    return any(path.startswith(prefix) for prefix in WHITE_LIST_PREFIXES) or any(
        path.endswith(suffix) for suffix in WHITE_LIST_SUFFIXES
    )
