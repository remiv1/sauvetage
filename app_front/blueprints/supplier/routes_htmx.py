"""Blueprint pour les fonctionnalités des fournisseurs pour la partie données."""

import json

from flask import Blueprint, make_response, request, render_template
from app_front.blueprints.supplier.utils import search_suppliers, create_supplier
from app_front.blueprints.supplier.forms import SupplierCreateForm

bp_supplier_htmx = Blueprint("supplier_htmx", __name__, url_prefix="/supplier/htmx")

ADD_FORM_TEMPLATE = "htmx_templates/supplier/add_supplier_form.html"


@bp_supplier_htmx.get("/get/suppliers/<type_of_data>")
def get_suppliers(type_of_data: str):
    """Retourne la liste des fournisseurs."""
    supplier_name = request.args.get("supplier_name", "")
    suppliers = search_suppliers(supplier_name, data_returned=type_of_data)
    if type_of_data == "id_name_gln":
        allow_create = request.args.get("allow_create", "false") == "true"
        context = request.args.get("context", "stock")
        return render_template(
            "htmx_templates/supplier/suppliers_dropdown.html",
            suppliers=suppliers,
            query=supplier_name,
            allow_create=allow_create,
            context=context,
        )
    if type_of_data == "filter":
        return render_template(
            "htmx_templates/supplier/filter_suppliers_dropdown.html",
            suppliers=suppliers,
            query=supplier_name,
        )
    raise ValueError(f"Type de données non supporté : {type_of_data}")


@bp_supplier_htmx.get("/add-new/<name>")
def add_new_supplier(name: str):
    """Affiche le formulaire d'ajout rapide d'un fournisseur."""
    form = SupplierCreateForm()
    form.supplier_name.data = name
    return render_template(ADD_FORM_TEMPLATE, form=form, name=name)


@bp_supplier_htmx.post("/create")
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
            print(f"Erreur lors de la création du fournisseur : {exc}")
            form.supplier_name.errors = list(form.supplier_name.errors) + [str(exc)]
            return render_template(ADD_FORM_TEMPLATE, form=form), 423
        # Succès : vider la modale et notifier l'application
        response = make_response("", 200)
        response.headers["HX-Trigger"] = json.dumps({"supplier:created": result})
        return response
    # Erreurs de validation : re-rendu du formulaire avec messages
    return render_template(ADD_FORM_TEMPLATE, form=form), 422


@bp_supplier_htmx.get("/select/<int:supplier_id>")
def select_supplier(supplier_id: int):
    """Retourne le fragment OOB de sélection d'un fournisseur.

    Le paramètre ``context`` ("stock" par défaut, ou "dilicom") détermine
    les IDs DOM utilisés pour les swaps OOB.
    """
    supplier_name = request.args.get("supplier_name", "")
    gln13 = request.args.get("gln13", "")
    context = request.args.get("context", "stock")
    allow_create = request.args.get("allow_create", "false") == "true"
    return render_template(
        "htmx_templates/supplier/select_supplier.html",
        supplier_id=supplier_id,
        supplier_name=supplier_name,
        gln13=gln13,
        context=context,
        allow_create=allow_create,
    )


@bp_supplier_htmx.get("/close-modal")
def close_modal():
    """Retourne un fragment vide pour fermer la modale HTMX."""
    return "", 200
