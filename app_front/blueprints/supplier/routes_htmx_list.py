"""Blueprint HTMX pour la gestion des fournisseurs (liste, modales)."""

from flask import Blueprint, make_response, render_template, request
from app_front.blueprints.supplier.forms import SupplierCreateForm, SupplierEditForm
from app_front.blueprints.supplier.utils import (
    search_suppliers_paginated,
    get_supplier_by_id,
    update_supplier_data,
    toggle_supplier_active,
    create_supplier,
)

bp_supplier_htmx_list = Blueprint(
    "supplier_htmx_list",
    __name__,
    url_prefix="/supplier/htmx/list",
)

SUPPLIER_TABLE = "htmx_templates/supplier/list/table.html"
SUPPLIER_VIEW_MODAL = "htmx_templates/supplier/list/view_modal.html"
SUPPLIER_EDIT_MODAL = "htmx_templates/supplier/list/edit_modal.html"
SUPPLIER_TOGGLE_MODAL = "htmx_templates/supplier/list/toggle_modal.html"
SUPPLIER_CREATE_MODAL = "htmx_templates/supplier/list/create_modal.html"
SUPPLIER_NOT_FOUND = "<p>Fournisseur introuvable.</p>"


@bp_supplier_htmx_list.get("/table")
def supplier_table():
    """Retourne le tableau filtré et paginé des fournisseurs (HTMX)."""
    name = request.args.get("name", "").strip() or None
    gln13 = request.args.get("gln13", "").strip() or None
    is_active_str = request.args.get("is_active", "").strip()
    is_active = None
    if is_active_str == "true":
        is_active = True
    elif is_active_str == "false":
        is_active = False

    page_str = request.args.get("page", "1").strip()
    page = max(1, int(page_str)) if page_str.isdigit() else 1

    result = search_suppliers_paginated(
        name=name, gln13=gln13, is_active=is_active, page=page,
    )
    return render_template(SUPPLIER_TABLE, **result)


@bp_supplier_htmx_list.get("/view/<int:supplier_id>")
def supplier_view(supplier_id: int):
    """Retourne la modale de consultation d'un fournisseur (HTMX)."""
    supplier = get_supplier_by_id(supplier_id)
    if supplier is None:
        return SUPPLIER_NOT_FOUND, 404
    return render_template(SUPPLIER_VIEW_MODAL, supplier=supplier)


@bp_supplier_htmx_list.get("/edit/<int:supplier_id>")
def supplier_edit_form(supplier_id: int):
    """Retourne la modale d'édition d'un fournisseur (HTMX)."""
    supplier = get_supplier_by_id(supplier_id)
    if supplier is None:
        return SUPPLIER_NOT_FOUND, 404
    form = SupplierEditForm()
    form.supplier_name.data = supplier["name"]
    form.gln13.data = supplier["gln13"]
    form.contact_email.data = supplier["contact_email"]
    form.contact_phone.data = supplier["contact_phone"]
    return render_template(SUPPLIER_EDIT_MODAL, form=form, supplier=supplier)


@bp_supplier_htmx_list.post("/edit/<int:supplier_id>")
def supplier_edit_submit(supplier_id: int):
    """Traite la soumission du formulaire d'édition (HTMX)."""
    form = SupplierEditForm()
    if form.validate_on_submit():
        data = {
            "name": form.supplier_name.data,
            "gln13": form.gln13.data,
            "contact_email": form.contact_email.data,
            "contact_phone": form.contact_phone.data,
        }
        try:
            update_supplier_data(supplier_id, data)
        except ValueError as exc:
            supplier = get_supplier_by_id(supplier_id) or {"id": supplier_id}
            form.supplier_name.errors = list(form.supplier_name.errors) + [str(exc)]
            return render_template(SUPPLIER_EDIT_MODAL, form=form, supplier=supplier), 422

        response = make_response("", 200)
        response.headers["HX-Trigger"] = "refreshSupplierTable"
        return response

    supplier = get_supplier_by_id(supplier_id) or {"id": supplier_id}
    return render_template(SUPPLIER_EDIT_MODAL, form=form, supplier=supplier), 422


@bp_supplier_htmx_list.get("/toggle/<int:supplier_id>")
def supplier_toggle_modal(supplier_id: int):
    """Retourne la modale de confirmation d'activation/désactivation (HTMX)."""
    supplier = get_supplier_by_id(supplier_id)
    if supplier is None:
        return SUPPLIER_NOT_FOUND, 404
    return render_template(SUPPLIER_TOGGLE_MODAL, supplier=supplier)


@bp_supplier_htmx_list.post("/toggle/<int:supplier_id>")
def supplier_toggle_submit(supplier_id: int):
    """Active ou désactive un fournisseur (HTMX)."""
    try:
        toggle_supplier_active(supplier_id)
    except ValueError:
        return "<p>Erreur lors du changement de statut.</p>", 422

    response = make_response("", 200)
    response.headers["HX-Trigger"] = "refreshSupplierTable"
    return response


@bp_supplier_htmx_list.get("/create")
def supplier_create_form():
    """Retourne la modale de création d'un fournisseur (HTMX)."""
    form = SupplierCreateForm()
    return render_template(SUPPLIER_CREATE_MODAL, form=form)


@bp_supplier_htmx_list.post("/create")
def supplier_create_submit():
    """Traite la soumission du formulaire de création (HTMX)."""
    form = SupplierCreateForm()
    if form.validate_on_submit():
        data = {
            "name": form.supplier_name.data,
            "gln13": form.gln13.data,
            "contact_email": form.contact_email.data,
            "contact_phone": form.contact_phone.data,
        }
        try:
            create_supplier(data)
        except ValueError as exc:
            form.supplier_name.errors = list(form.supplier_name.errors) + [str(exc)]
            return render_template(SUPPLIER_CREATE_MODAL, form=form), 422

        response = make_response("", 200)
        response.headers["HX-Trigger"] = "refreshSupplierTable"
        return response

    return render_template(SUPPLIER_CREATE_MODAL, form=form), 422
