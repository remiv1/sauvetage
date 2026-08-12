#!/usr/bin/env python3
"""Génère la règle Traefik pour bloquer les chemins de bots depuis une liste de regex."""

from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "dynamic" / "bot_patterns.txt"
DEFAULT_OUTPUT = ROOT / "dynamic" / "bot-blockers.yml"


def read_patterns(path: Path) -> list[str]:
    """Lit la liste de motifs de bot, en gardant les regex telles quelles."""
    patterns: list[str] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        if line.startswith("raw:"):
            pattern = line[4:].strip()
        else:
            pattern = line

        if pattern:
            patterns.append(pattern)

    if not patterns:
        raise ValueError(f"Aucun motif trouvé dans {path}")

    return patterns


def render_yaml(patterns: list[str]) -> str:
    """Construit le YAML Traefik pour les routers de blocage."""
    regex = "|".join(patterns)
    return (
        "http:\n"
        "  routers:\n"
        "    block-bots-http:\n"
        f"      rule: 'PathRegexp(`(?i)({regex})`)'\n"
        "      priority: 1000\n"
        "      entryPoints:\n"
        "        - web\n"
        "      middlewares:\n"
        "        - bot-blocker\n"
        "      service: noop\n\n"
        "    block-bots-https:\n"
        f"      rule: 'PathRegexp(`(?i)({regex})`)'\n"
        "      priority: 1000\n"
        "      entryPoints:\n"
        "        - websecure\n"
        "      middlewares:\n"
        "        - bot-blocker\n"
        "      service: noop\n"
        "      tls:\n"
        "        certResolver: letsencrypt\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Fichier de motifs à bloquer")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Fichier YAML Traefik généré")
    args = parser.parse_args()

    patterns = read_patterns(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render_yaml(patterns), encoding="utf-8")
    print(f"Règle Traefik générée: {args.output}")


if __name__ == "__main__":
    main()
