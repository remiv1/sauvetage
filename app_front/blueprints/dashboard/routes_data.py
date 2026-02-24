"""Blueprint pour les fonctionnalités du tableau de bord (API JSON)

Endpoints:
- /dashboard/data/finances
- /dashboard/data/commandes
- /dashboard/data/stock
"""

from flask import Blueprint, jsonify

bp_dashboard_data = Blueprint("dashboard_data", __name__, url_prefix="/dashboard/data")

@bp_dashboard_data.route("/finances", methods=["GET"])
def finances():
    """Retourne les KPIs financiers pour une plage donnée.

    Query params:
    - start_date,
    - range (A, S, T, M, W) : Annual, Semestrial, Trimestrial, Monthly, Weekly
    - kpis (list[str]):
        - ca_sum: CA total
        - ca_paid: CA payé
        - ca_outstanding: CA à encaisser
        - average_margin: marge moyenne
        - pending_invoicing: en attente de facturation
        - pending_shipment: en attente d'envoi
    """
    #TODO: To implement
    return jsonify(
            {
            "months": [
                'Janvier',
                'Février',
                'Mars',
                'Avril',
                'Mai',
                'Juin',
                'Juillet',
                'Août',
                'Septembre',
                'Octobre',
                'Novembre',
                'Décembre'
            ],
            "charges": [30, 35, 38, 42, 39, 45, 40, 36, 44, 48, 46, 50],
            "ressources": [45, 52, 48, 61, 55, 67, 58, 49, 62, 72, 66, 76]
        }
    )

@bp_dashboard_data.route("/commandes", methods=["GET"])
def commandes():
    """Liste des commandes avec filtres de base pour le dashboard.

    Query params:
    - status (ex: pending, shipped, cancelled)
    - search (sur référence)
    - page, per_page pour pagination (optional, défaut page=1, per_page=25)
    - start_date (optional, pour filtrer par date de création),
    - range (A, S, T, M, W) : Annual, Semestrial, Trimestrial, Monthly, Weekly (optional)
    """
    #TODO: To implement
    return jsonify(
        [
            {
                "name": "M Rémi Verschuur",
                "date": "01/01/2026",
                "amount": 1253,
                "availability": "Disponible",
                "status": "En cours"
            },
            {
                "name": "M Christian de la Pellequirole",
                "date": "03/01/2026",
                "amount": 126.32,
                "availability": "Disponible",
                "status": "Annulée"
            }
        ]
    )

@bp_dashboard_data.route("/stock", methods=["GET"])
def stock():
    """Endpoints pour vues stock: slow_moving ou by_category

    Query params:
    - view=slow_moving|by_category,
    - limit,
    - category_id,
    - range
    """
    #TODO: To implement
    return jsonify(
        {
            "labels": [
                'Livres Ados',
                'Petite enfance',
                'Jeunesse',
                'Spiritualité',
                'Foyer',
                'Objets'
            ],
            "values": [503, 652, 498, 395, 198, 760],
            "value_total": 55300,
            "items_total": 3006
        }
    )
