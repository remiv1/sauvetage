#!/usr/bin/env python3
"""Génère un rapport Markdown horodaté depuis le rapport JSON de coverage."""

import json
import sys
from datetime import datetime
from pathlib import Path


GROUPS = {
    "Backend": "app_back/",
    "Frontend": "app_front/",
    "Base de données": "db_models/",
}


def percentage(covered: int, total: int) -> float:
    """Calcule un pourcentage de couverture sans division par zéro."""
    return (covered / total * 100) if total else 100.0


def parse_coverage(json_file: Path) -> dict[str, tuple[int, int]]:
    """Agrège les lignes couvertes et pertinentes par périmètre applicatif."""
    coverage: dict[str, list[int]] = {name: [0, 0] for name in GROUPS}
    report = json.loads(json_file.read_text(encoding="utf-8"))

    for filename, file_report in report["files"].items():
        normalized_filename = filename.replace("\\", "/")
        for group, prefix in GROUPS.items():
            if normalized_filename.startswith(prefix):
                summary = file_report["summary"]
                coverage[group][1] += summary["num_statements"]
                coverage[group][0] += summary["covered_lines"]
                break

    return {name: (values[0], values[1]) for name, values in coverage.items()}


def generate_report(coverage: dict[str, tuple[int, int]], output_file: Path) -> None:
    """Écrit le rapport Markdown de couverture global et détaillé par périmètre."""
    covered = sum(values[0] for values in coverage.values())
    total = sum(values[1] for values in coverage.values())
    rows = [
        ("Global", covered, total),
        *[(name, values[0], values[1]) for name, values in coverage.items()],
    ]
    report = [
        "# Rapport de couverture",
        "",
        f"**Date :** {datetime.now().isoformat(timespec='seconds')}",
        "",
        "| Périmètre | Lignes couvertes | Lignes pertinentes | Couverture |",
        "| --- | ---: | ---: | ---: |",
    ]
    for name, group_covered, group_total in rows:
        report.append(
            f"| {name} | {group_covered} | {group_total} | "
            f"{percentage(group_covered, group_total):.1f}% |"
        )
    output_file.write_text("\n".join(report) + "\n", encoding="utf-8")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("Usage: generate_coverage_report.py <coverage.json> <rapport.md>")
    json_path = Path(sys.argv[1])
    report_path = Path(sys.argv[2])
    generate_report(parse_coverage(json_path), report_path)
