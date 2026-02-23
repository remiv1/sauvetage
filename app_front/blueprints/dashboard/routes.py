"""Blueprint pour les fonctionnalités du tableau de bord"""

from flask import Blueprint, render_template, jsonify
from app_front.utils.pages import load_page_params

bp_dashboard = Blueprint("dashboard", __name__, url_prefix="/dashboard")


@bp_dashboard.route("/")
def index():
    """Page principale du tableau de bord."""
    config = load_page_params("dashboard")
    params = config.get("params", {})
    return render_template("dashboard/dashboard.html", params=params)


def _data_general() -> dict:
    return {
        "kpis": [
            {"label": "Chiffre d'affaires (mois)", "value": "24 850 €", "trend": "+8 %", "up": True, "icon": "euro"},
            {"label": "Commandes en cours", "value": "37", "trend": "+3", "up": True, "icon": "cart"},
            {"label": "Articles en rupture", "value": "12", "trend": "-2", "up": False, "icon": "box"},
            {"label": "Clients actifs", "value": "1 204", "trend": "+15", "up": True, "icon": "users"},
        ],
        "recent": [
            {"date": "23/02/2026", "type": "Commande", "ref": "CMD-2026-0341", "montant": "189,90 €", "statut": "En cours"},
            {"date": "23/02/2026", "type": "Commande", "ref": "CMD-2026-0340", "montant": "54,00 €", "statut": "Livrée"},
            {"date": "22/02/2026", "type": "Livraison", "ref": "LIV-2026-0112", "montant": "340,50 €", "statut": "Livrée"},
            {"date": "22/02/2026", "type": "Commande", "ref": "CMD-2026-0339", "montant": "22,00 €", "statut": "Annulée"},
            {"date": "21/02/2026", "type": "Commande", "ref": "CMD-2026-0338", "montant": "97,40 €", "statut": "En cours"},
        ],
    }


def _data_stocks() -> dict:
    return {
        "kpis": [
            {"label": "Articles en stock", "value": "8 432", "trend": "-24", "up": False, "icon": "box"},
            {"label": "Valeur du stock", "value": "142 300 €", "trend": "+1,2 %", "up": True, "icon": "euro"},
            {"label": "Ruptures de stock", "value": "12", "trend": "-2", "up": False, "icon": "alert"},
            {"label": "Réapprovisionnements", "value": "5", "trend": "0", "up": True, "icon": "truck"},
        ],
        "items": [
            {"ref": "LIV-001234", "titre": "Les Misérables", "stock": 3, "min_stock": 5, "statut": "Critique"},
            {"ref": "LIV-002891", "titre": "Le Petit Prince", "stock": 48, "min_stock": 10, "statut": "OK"},
            {"ref": "LIV-003210", "titre": "Madame Bovary", "stock": 7, "min_stock": 8, "statut": "Faible"},
            {"ref": "MED-000512", "titre": "Audiothèque Proust", "stock": 2, "min_stock": 3, "statut": "Critique"},
            {"ref": "LIV-005601", "titre": "L'Étranger", "stock": 21, "min_stock": 10, "statut": "OK"},
        ],
    }


def _data_commandes() -> dict:
    return {
        "kpis": [
            {"label": "Commandes du jour", "value": "18", "trend": "+4", "up": True, "icon": "cart"},
            {"label": "En attente", "value": "37", "trend": "-1", "up": False, "icon": "clock"},
            {"label": "En livraison", "value": "14", "trend": "+2", "up": True, "icon": "truck"},
            {"label": "Livrées (mois)", "value": "312", "trend": "+22 %", "up": True, "icon": "check"},
        ],
        "commandes": [
            {"ref": "CMD-2026-0341", "client": "Librairie du Midi", "date": "23/02/2026", "total": "189,90 €", "statut": "En cours"},
            {"ref": "CMD-2026-0340", "client": "FNAC Paris", "date": "23/02/2026", "total": "54,00 €", "statut": "Livrée"},
            {"ref": "CMD-2026-0339", "client": "Amazon FR", "date": "22/02/2026", "total": "22,00 €", "statut": "Annulée"},
            {"ref": "CMD-2026-0338", "client": "Gibert Joseph", "date": "21/02/2026", "total": "97,40 €", "statut": "En cours"},
            {"ref": "CMD-2026-0337", "client": "Cultura Lyon", "date": "21/02/2026", "total": "215,00 €", "statut": "Livrée"},
        ],
    }


def _data_clients() -> dict:
    return {
        "kpis": [
            {"label": "Clients totaux", "value": "2 187", "trend": "+32 (mois)", "up": True, "icon": "users"},
            {"label": "Nouveaux (mois)", "value": "32", "trend": "+8 %", "up": True, "icon": "user-plus"},
            {"label": "Actifs (30 j)", "value": "1 204", "trend": "+5 %", "up": True, "icon": "activity"},
            {"label": "Panier moyen", "value": "78,40 €", "trend": "+3,2 %", "up": True, "icon": "euro"},
        ],
        "clients": [
            {"nom": "Librairie du Midi", "ville": "Marseille", "commandes": 24, "ca": "4 560,00 €", "statut": "Actif"},
            {"nom": "FNAC Paris", "ville": "Paris", "commandes": 18, "ca": "3 240,00 €", "statut": "Actif"},
            {"nom": "Gibert Joseph", "ville": "Paris", "commandes": 12, "ca": "1 870,00 €", "statut": "Actif"},
            {"nom": "Cultura Lyon", "ville": "Lyon", "commandes": 9, "ca": "1 230,00 €", "statut": "Actif"},
            {"nom": "Librairie Mollat", "ville": "Bordeaux", "commandes": 7, "ca": "980,00 €", "statut": "Inactif"},
        ],
    }


def _data_fournisseurs() -> dict:
    return {
        "kpis": [
            {"label": "Fournisseurs actifs", "value": "28", "trend": "+1", "up": True, "icon": "truck"},
            {"label": "Commandes en cours", "value": "9", "trend": "+2", "up": True, "icon": "cart"},
            {"label": "Livraisons attendues", "value": "5", "trend": "-1", "up": False, "icon": "clock"},
            {"label": "Délai moyen (j)", "value": "4,2", "trend": "-0,3", "up": False, "icon": "activity"},
        ],
        "fournisseurs": [
            {"nom": "Hachette Livre", "pays": "France", "commandes": 3, "delai": "3 j", "statut": "Actif"},
            {"nom": "Gallimard Distribution", "pays": "France", "commandes": 2, "delai": "4 j", "statut": "Actif"},
            {"nom": "Interference Book", "pays": "Belgique", "commandes": 1, "delai": "6 j", "statut": "Actif"},
            {"nom": "Librimundi", "pays": "Suisse", "commandes": 0, "delai": "—", "statut": "Inactif"},
            {"nom": "PUF Distribution", "pays": "France", "commandes": 1, "delai": "5 j", "statut": "Actif"},
        ],
    }


_DATA_HANDLERS = {
    "general": _data_general,
    "stocks": _data_stocks,
    "commandes": _data_commandes,
    "clients": _data_clients,
    "fournisseurs": _data_fournisseurs,
}


@bp_dashboard.route("/api/<string:tab_name>")
def api_data(tab_name: str):
    """Endpoint JSON pour les données d'un onglet du tableau de bord."""
    handler = _DATA_HANDLERS.get(tab_name)
    if handler is None:
        return jsonify({"error": "Onglet inconnu"}), 404
    return jsonify(handler())
