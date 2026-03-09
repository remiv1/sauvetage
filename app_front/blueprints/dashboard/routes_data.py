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
    # TODO: To implement
    months = [
        "Janvier",
        "Février",
        "Mars",
        "Avril",
        "Mai",
        "Juin",
        "Juillet",
        "Août",
        "Septembre",
        "Octobre",
        "Novembre",
        "Décembre",
    ]
    charges = [30, 35, 38, 42, 39, 45, 40, 36, 44, 48, 46, 50]
    ressources = [45, 52, 48, 61, 55, 67, 58, 49, 62, 72, 66, 76]
    return jsonify({"months": months, "charges": charges, "ressources": ressources})


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
    # TODO: To implement
    names = [
        "M Rémi Verschuur",
        "M Christian de la Pellequirole",
        "Mme Sophie Martin",
        "M Jean Dupont",
        "Mme Marie Curie",
        "M Paul Durand",
        "Mme Claire Lefevre",
        "M Jacques Moreau",
        "Mme Isabelle Dubois",
        "M François Petit",
    ]
    order_dates = [
        "01/01/2026",
        "03/01/2026",
        "05/01/2026",
        "07/01/2026",
        "09/01/2026",
        "11/01/2026",
        "13/01/2026",
        "15/01/2026",
        "17/01/2026",
        "19/01/2026",
    ]
    amounts = [
        1253,
        126.32,
        789.45,
        456.78,
        234.56,
        890.12,
        345.67,
        678.90,
        123.45,
        567.89,
    ]
    availabilities = [
        "Disponible",
        "Indisponible",
        "Disponible",
        "Indisponible",
        "Disponible",
        "Partielle",
        "Disponible",
        "Indisponible",
        "Disponible",
        "Partielle",
    ]
    status = [
        "En cours",
        "Annulée",
        "En cours",
        "Expédiée",
        "En cours",
        "Annulée",
        "Expédiée",
        "En cours",
        "Expédiée",
        "En cours",
    ]
    orders = []
    for i, _ in enumerate(names):
        orders.append(
            {
                "name": names[i],
                "date": order_dates[i],
                "amount": amounts[i],
                "availability": availabilities[i],
                "status": status[i],
            }
        )

    return jsonify(orders)


@bp_dashboard_data.route("/stock", methods=["GET"])
def stock():
    """Endpoints pour vues stock: slow_moving ou by_category

    Query params:
    - view=slow_moving|by_category,
    - limit,
    - category_id,
    - range
    """
    # TODO: To implement
    labels = [
        "Livres Ados",
        "Petite enfance",
        "Jeunesse",
        "Spiritualité",
        "Foyer",
        "Objets",
    ]
    values = [503, 652, 498, 395, 198, 760]
    return jsonify(
        {
            "labels": labels,
            "values": values,
            "value_total": sum(values),
            "items_total": len(labels),
        }
    )
