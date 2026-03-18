"""Blueprint pour les fonctionnalités des fournisseurs pour la partie données."""

import json

from flask import Blueprint, make_response, request, render_template
from app_front.blueprints.supplier.utils import search_suppliers, create_supplier
from app_front.blueprints.supplier.forms import SupplierCreateForm

bp_supplier_htmx = Blueprint("supplier_htmx", __name__, url_prefix="/supplier/htmx")

ADD_FORM_TEMPLATE = "htmx_templates/supplier/add_supplier_form.html"


@bp_supplier_htmx.get("/get/suppliers/<type_of_data>")
def get_suppliers(type_of_data: str):
    """Retourne la liste des fournisseurs"""
    supplier_name = request.args.get("supplier_name", "")
    suppliers = search_suppliers(supplier_name, data_returned=type_of_data)
    if type_of_data == "id_name_gln":
        return render_template(
            "htmx_templates/supplier/dilicom_suppliers_dropdown.html",
            suppliers=suppliers,
            query=supplier_name,
        )
    if type_of_data == "filter":
        return render_template(
            "htmx_templates/supplier/filter_suppliers_dropdown.html",
            suppliers=suppliers,
            query=supplier_name,
        )
    return render_template(
        "htmx_templates/supplier/suppliers_dropdown.html",
        suppliers=suppliers,
        query=supplier_name,
    )


@bp_supplier_htmx.get("/add-new/<name>")
def add_new_supplier(name: str):
    """Affiche le formulaire d'ajout rapide d'un fournisseur."""
    form = SupplierCreateForm()
    form.supplier_name.data = name
    return render_template(ADD_FORM_TEMPLATE, form=form, name=name)


@bp_supplier_htmx.route("/create", methods=["POST"])
def create_supplier_htmx():
    """Crée un fournisseur via HTMX (form-encoded + WTForms)."""
    form = SupplierCreateForm()
    if form.validate_on_submit():
        data = {
            "name": form.supplier_name.data,
            "gln13": form.gln13.data,
            "contact_email": form.contact_email.data,
            "contact_phone": form.contact_phone.data,
        }
        try:
            result = create_supplier(data)
        except ValueError as exc:
            form.supplier_name.errors = list(form.supplier_name.errors) + [str(exc)]
            return render_template(ADD_FORM_TEMPLATE, form=form), 422
        # Succès : vider la modale et notifier l'application
        response = make_response("", 200)
        response.headers["HX-Trigger"] = json.dumps({"supplier:created": result})
        return response
    # Erreurs de validation : re-rendu du formulaire avec messages
    return render_template(ADD_FORM_TEMPLATE, form=form), 422


@bp_supplier_htmx.get("/select/<int:supplier_id>")
def select_supplier(supplier_id: int):
    """Retourne le fragment de sélection d'un fournisseur (id + nom via OOB)."""
    supplier_name = request.args.get("supplier_name", "")
    return render_template(
        "htmx_templates/supplier/select_supplier.html",
        supplier_id=supplier_id,
        supplier_name=supplier_name,
    )


@bp_supplier_htmx.get("/select/dilicom/<int:supplier_id>")
def select_dilicom_supplier(supplier_id: int):
    """Retourne les fragments OOB pour la sélection d'un fournisseur dans le contexte Dilicom."""
    supplier_name = request.args.get("supplier_name", "")
    gln13 = request.args.get("gln13", "")
    return render_template(
        "htmx_templates/supplier/select_dilicom_supplier.html",
        supplier_id=supplier_id,
        supplier_name=supplier_name,
        gln13=gln13,
    )


@bp_supplier_htmx.get("/close-modal")
def close_modal():
    """Retourne un fragment vide pour fermer la modale HTMX."""
    return "", 200
