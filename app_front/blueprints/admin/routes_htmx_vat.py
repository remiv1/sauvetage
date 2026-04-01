"""Routes HTMX pour la gestion des taux de TVA (admin)."""

from datetime import datetime
import json
from flask import Blueprint, render_template, request, make_response
from app_front.utils.decorators import permission_required, ADMIN, SUPER_ADMIN
from app_front.blueprints.admin.forms import VatRateForm
from app_front.blueprints.admin.utils import (
    get_vat_rates_paginated,
    get_vat_rate_by_id,
    create_vat_rate,
    update_vat_rate,
    close_vat_rate,
)

bp_admin_vat = Blueprint("admin_vat", __name__, url_prefix="/admin/htmx/vat")

VAT_TABLE = "htmx_templates/admin/vat/table.html"
VAT_CREATE_MODAL = "htmx_templates/admin/vat/create_modal.html"
VAT_EDIT_MODAL = "htmx_templates/admin/vat/edit_modal.html"
VAT_CLOSE_MODAL = "htmx_templates/admin/vat/close_modal.html"
VAT_NOT_FOUND = "<p>Taux de TVA introuvable.</p>"


@bp_admin_vat.get("/table")
@permission_required([ADMIN, SUPER_ADMIN], _and=False)
def vat_table():
    """Tableau paginé et filtré des taux de TVA."""
    code_str = request.args.get("code", "").strip()
    code = int(code_str) if code_str.isdigit() else None
    active_only_str = request.args.get("active_only", "")
    active_only = active_only_str == "true"
    page_str = request.args.get("page", "1").strip()
    page = max(1, int(page_str)) if page_str.isdigit() else 1

    result = get_vat_rates_paginated(code=code, active_only=active_only, page=page)
    return render_template(VAT_TABLE, **result)


@bp_admin_vat.get("/create-form")
@permission_required([ADMIN, SUPER_ADMIN], _and=False)
def vat_create_form():
    """Modale de création d'un taux de TVA."""
    form = VatRateForm()
    return render_template(VAT_CREATE_MODAL, form=form)


@bp_admin_vat.post("/create")
@permission_required([ADMIN, SUPER_ADMIN], _and=False)
def vat_create():
    """Crée un taux de TVA."""
    form = VatRateForm()
    if form.validate_on_submit():
        data = {
            "code": form.code.data,
            "rate": float(form.rate.data),  # type: ignore
            "label": form.label.data,
            "date_start": form.date_start.data,
            "date_end": form.date_end.data,
        }
        try:
            create_vat_rate(data)
        except ValueError as exc:
            form.label.errors = list(form.label.errors) + [str(exc)]
            return render_template(VAT_CREATE_MODAL, form=form), 422
        response = make_response("", 200)
        response.headers["HX-Trigger"] = json.dumps({"vat:created": True})
        return response
    return render_template(VAT_CREATE_MODAL, form=form), 422


@bp_admin_vat.get("/edit/<int:vat_id>")
@permission_required([ADMIN, SUPER_ADMIN], _and=False)
def vat_edit_form(vat_id: int):
    """Modale d'édition d'un taux de TVA."""
    rate = get_vat_rate_by_id(vat_id)
    if rate is None:
        return VAT_NOT_FOUND, 404
    form = VatRateForm()
    form.code.data = rate["code"]
    form.rate.data = rate["rate"]
    form.label.data = rate["label"]
    if rate["date_start"]:
        try:
            form.date_start.data = datetime.fromisoformat(rate["date_start"])
        except ValueError:
            pass
    if rate["date_end"]:
        try:
            form.date_end.data = datetime.fromisoformat(rate["date_end"])
        except ValueError:
            pass
    return render_template(VAT_EDIT_MODAL, form=form, vat=rate)


@bp_admin_vat.post("/edit/<int:vat_id>")
@permission_required([ADMIN, SUPER_ADMIN], _and=False)
def vat_edit_submit(vat_id: int):
    """Traite la modification d'un taux de TVA."""
    rate = get_vat_rate_by_id(vat_id)
    if rate is None:
        return VAT_NOT_FOUND, 404
    form = VatRateForm()
    if form.validate_on_submit():
        data = {
            "code": form.code.data,
            "rate": float(form.rate.data),  # type: ignore
            "label": form.label.data,
            "date_start": form.date_start.data,
            "date_end": form.date_end.data,
        }
        try:
            update_vat_rate(vat_id, data)
        except ValueError as exc:
            form.label.errors = list(form.label.errors) + [str(exc)]
            return render_template(VAT_EDIT_MODAL, form=form, vat=rate), 422
        response = make_response("", 200)
        response.headers["HX-Trigger"] = json.dumps({"vat:updated": True})
        return response
    return render_template(VAT_EDIT_MODAL, form=form, vat=rate), 422


@bp_admin_vat.get("/close-form/<int:vat_id>")
@permission_required([ADMIN, SUPER_ADMIN], _and=False)
def vat_close_form(vat_id: int):
    """Modale de confirmation de clôture d'un taux de TVA."""
    rate = get_vat_rate_by_id(vat_id)
    if rate is None:
        return VAT_NOT_FOUND, 404
    return render_template(VAT_CLOSE_MODAL, vat=rate)


@bp_admin_vat.post("/close/<int:vat_id>")
@permission_required([ADMIN, SUPER_ADMIN], _and=False)
def vat_close(vat_id: int):
    """Clôture un taux de TVA (met date_end = maintenant)."""
    ok = close_vat_rate(vat_id)
    if not ok:
        return VAT_NOT_FOUND, 404
    response = make_response("", 200)
    response.headers["HX-Trigger"] = json.dumps({"vat:closed": True})
    return response
