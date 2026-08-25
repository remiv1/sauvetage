"""Blueprint pour les fonctionnalités de gestion des stocks"""

from datetime import datetime
from pathlib import Path
from typing import Any
import toml

from flask import Blueprint, flash, make_response, redirect, request, send_file, url_for
from app_front.utils.pages import render_page
from app_front.blueprints.stock.utils import (
    is_zero_price_items,
    get_zero_price_items,
    get_supplier_orders,
    get_order_by_id,
    create_order_in_db,
    trigger_catalog_wc_sync,
)
from app_front.blueprints.stock.forms import OrderInCreateForm
from app_front.utils.documents import build_qrcode_data_uri, create_pdf_from_template

PDF_MIMETYPE = "application/pdf"

bp_stock = Blueprint("stock", __name__, url_prefix="/stock")


def get_company_config() -> dict:
    """Charge les informations de l'entreprise cliente depuis la config TOML."""
    company_file = Path(__file__).resolve().parents[2] / "config" / "company.toml"
    data = toml.load(company_file)
    return data.get("company", {})


@bp_stock.route("/", methods=["GET"])
def index():
    """Page d'accueil du module stocks"""
    has_zero_price_items = is_zero_price_items()
    return render_page("stock_index", has_zero_price_items=has_zero_price_items)

# ——————————————————————— Conciliation de stocks ———————————————————————

@bp_stock.route("/council", methods=["GET", "POST"])
def council():
    """Page de gestion de réconciliation des prix de stocks"""
    items_to_council = get_zero_price_items()
    return render_page("stock_council", items_to_council=items_to_council)

# ——————————————————————— Commandes & Retours de stocks ———————————————————————

@bp_stock.route("/orders", methods=["GET", "POST"])
def orders():
    """Page de gestion des commandes fournisseurs (entrantes)"""
    form = OrderInCreateForm()
    orders_list = get_supplier_orders()
    if form.validate_on_submit():
        try:
            create_order_in_db(form)
            flash("Commande créée avec succès.", "success")
            return redirect(url_for("stock_htmx.new_order_table"))
        except (ValueError, RuntimeError) as exc:
            flash(str(exc), "error")
    if form.validate_on_submit():
        try:
            create_order_in_db(form)
            flash("Commande créée avec succès.", "success")
            return redirect(url_for("stock_htmx.new_order_table"))
        except (ValueError, RuntimeError) as exc:
            flash(str(exc), "error")
    return render_page("stock_order", orders=orders_list)


@bp_stock.route("/orders/<int:order_id>", methods=["GET"])
def order_view(order_id: int):
    """Route d'acces direct a une commande fournisseur (QR / URL partageable)."""
    modal = request.args.get("modal", "view")
    return render_page("stock_order", open_order_id=order_id, modal=modal)


@bp_stock.route("/orders/<int:order_id>/slip.pdf", methods=["GET"])
def order_download_slip(order_id: int):
    """Telecharge le bon de commande fournisseur (A4 paysage N&B)."""
    order = get_order_by_id(order_id)

    open_url = url_for("stock.order_view", order_id=order_id, modal="view", _external=True)
    qr_code_data_uri = build_qrcode_data_uri(open_url)

    lines = []
    total_ht = 0.0
    for line in (order.orderin_lines or []):
        if line.line_state == "cancelled":
            continue
        unit_price = float(line.get_unit_price_ht())
        line_total = float(line.qty_ordered or 0) * unit_price
        total_ht += line_total
        lines.append(
            {
                "article_name": line.general_object.name \
                    if line.general_object \
                    else f"Article #{line.general_object_id}",
                "ean13": getattr(line.general_object, "ean13", None) or "-",
                "quantity": int(line.qty_ordered or 0),
                "unit_price": f"{unit_price:.2f} EUR",
                "prices": [
                    {
                        "unit_price": f"{float(price.unit_price):.2f} EUR",
                        "vat_rate": f"{float(price.vat_rate):g} %",
                    }
                    for price in line.prices
                ],
                "line_total_ht": f"{line_total:.2f} EUR",
            }
        )

    company = get_company_config()
    pdf_stream, filename = create_pdf_from_template(
        "pdf/supplier_order_slip.html",
        {
            "order": {
                "reference": order.order_ref,
                "external_ref": order.external_ref or "-",
                "supplier_name": order.supplier.name if order.supplier else "-",
                "state": order.order_state,
                "date": datetime.now().strftime("%d/%m/%Y"),
            },
            "company": {
                "name": company.get("name", "-"),
                "address": company.get("address", "-"),
                "siret": company.get("siret", "-"),
                "greffe": company.get("greffe", "-"),
                "naf": company.get("naf", "-"),
                "tva": company.get("tva", "-"),
                "tel": company.get("tel", "-"),
                "email": company.get("mail", "-"),
            },
            "lines": lines,
            "total_ht": f"{total_ht:.2f} EUR",
            "internal": True,
            "qr_code_data_uri": qr_code_data_uri,
        },
        fallback_filename=f"{order.order_ref}.pdf",
    )
    return send_file(
        pdf_stream,
        mimetype=PDF_MIMETYPE,
        as_attachment=True,
        download_name=filename,
    )


@bp_stock.route("/orders/new", methods=["GET", "POST"])
def create_order():
    """Création d'une nouvelle commande fournisseur"""
    return render_page("stock_order")


@bp_stock.route("/returns/new", methods=["GET", "POST"])
def create_return():
    """Création d'un retour fournisseur."""
    form = OrderInCreateForm()
    returns_list = get_supplier_orders(out=True)
    if form.validate_on_submit():
        try:
            create_order_in_db(form, out=True)
            flash("Retour fournisseur créé avec succès.", "success")
            return redirect(url_for("stock_htmx_return.returns"))
        except (ValueError, RuntimeError) as exc:
            flash(str(exc), "error")
    return render_page("stock_returns", returns=returns_list)


@bp_stock.route("/returns/<int:order_id>", methods=["GET"])
def return_view(order_id: int):
    """Route d'accès direct à un retour fournisseur (QR / URL partageable)."""
    modal = request.args.get("modal", "view")
    return render_page("stock_returns", open_order_id=order_id, modal=modal)


def _build_return_slip_line(line: Any) -> dict[str, Any] | None:
    """Construit le dictionnaire représentant une ligne du bon de retour."""
    if line.line_state == "cancelled":
        return None
    unit_price = float(line.get_unit_price_ht())
    line_total = float(line.qty_ordered or 0) * unit_price
    return {
        "article_name": line.general_object.name
            if line.general_object
            else f"Article #{line.general_object_id}",
        "ean13": getattr(line.general_object, "ean13", None) or "-",
        "quantity": int(line.qty_ordered or 0),
        "unit_price": f"{unit_price:.2f} EUR",
        "prices": [
            {
                "unit_price": f"{float(price.unit_price):.2f} EUR",
                "vat_rate": f"{float(price.vat_rate):g} %",
            }
            for price in line.prices
        ],
        "line_total_ht": f"{line_total:.2f} EUR",
        "line_total_value": line_total,
    }


@bp_stock.route("/returns/<int:order_id>/slip.pdf", methods=["GET"])
def return_download_slip(order_id: int):
    """Télécharge le bon de retour fournisseur (A4 paysage N&B)."""
    order = get_order_by_id(order_id)

    open_url = url_for("stock.order_view", order_id=order_id, modal="view", _external=True)
    qr_code_data_uri = build_qrcode_data_uri(open_url)

    lines: list[dict[str, Any]] = []
    total_ht = 0.0
    for line in (order.orderin_lines or []):
        slip_line = _build_return_slip_line(line)
        if slip_line is None:
            continue
        lines.append(slip_line)
        total_ht += slip_line["line_total_value"]

    company = get_company_config()
    supplier = order.supplier
    pdf_stream, filename = create_pdf_from_template(
        "pdf/supplier_return_slip.html",
        {
            "order": {
                "reference": order.order_ref,
                "external_ref": order.external_ref or "-",
                "supplier_name": supplier.name if supplier else "-",
                "state": order.order_state,
                "date": datetime.now().strftime("%d/%m/%Y"),
            },
            "supplier": {
                "name": supplier.name if supplier else "-",
                "address": supplier.address or "-",
                "siren_siret": supplier.siren_siret or "-",
                "vat_number": supplier.vat_number or "-",
                "contact_phone": supplier.contact_phone or "-",
                "contact_email": supplier.contact_email or "-",
            },
            "company": {
                "name": company.get("name", "-"),
                "address": company.get("address", "-"),
                "siret": company.get("siret", "-"),
                "greffe": company.get("greffe", "-"),
                "naf": company.get("naf", "-"),
                "tva": company.get("tva", "-"),
                "tel": company.get("tel", "-"),
                "email": company.get("mail", "-"),
            },
            "lines": lines,
            "total_ht": f"{total_ht:.2f} EUR",
            "internal": True,
            "qr_code_data_uri": qr_code_data_uri,
        },
        fallback_filename=f"{order.order_ref}.pdf",
    )
    return send_file(
        pdf_stream,
        mimetype=PDF_MIMETYPE,
        as_attachment=True,
        download_name=filename,
    )


# ——————————————————————— Réservations de stocks ———————————————————————

@bp_stock.route("/reservations", methods=["GET"])
def reservations():
    """Page de gestion des réservations de stocks"""
    orders_list = get_supplier_orders(reservation=True)
    return render_page("stock_reservations", orders=orders_list, reservation=True)


@bp_stock.route("/reservations/<int:order_id>", methods=["GET"])
def reservation_view(order_id: int):
    """Route d'acces direct a une reservation (QR / URL partageable)."""
    modal = request.args.get("modal", "view")
    return render_page(
        "stock_reservations",
        open_order_id=order_id,
        modal=modal,
        reservation=True,
    )


@bp_stock.route("/reservations/<int:order_id>/slip.pdf", methods=["GET"])
def reservation_download_slip(order_id: int):
    """Telecharge le bon de reservation (A4 paysage + QR de validation retour)."""
    order = get_order_by_id(order_id)

    validate_url = url_for(
        "stock.reservation_view",
        order_id=order_id,
        modal="validate",
        _external=True,
    )
    qr_code_data_uri = build_qrcode_data_uri(validate_url)

    lines = []
    total_ht = 0.0
    for line in (order.orderin_lines or []):
        if line.line_state == "cancelled":
            continue
        unit_price = float(line.get_unit_price_ht())
        line_total = float(line.qty_ordered or 0) * unit_price
        total_ht += line_total
        lines.append(
            {
                "article_name": line.general_object.name \
                    if line.general_object \
                    else f"Article #{line.general_object_id}",
                "quantity": int(line.qty_ordered or 0),
                "line_state": line.line_state,
                "unit_price": f"{unit_price:.2f} EUR",
                "prices": [
                    {
                        "unit_price": f"{float(price.unit_price):.2f} EUR",
                        "vat_rate": f"{float(price.vat_rate):g} %",
                    }
                    for price in line.prices
                ],
                "line_total_ht": f"{line_total:.2f} EUR",
            }
        )

    reservation_context = order.reservation_context or {}
    pdf_stream, filename = create_pdf_from_template(
        "pdf/reservation_slip.html",
        {
            "order": {
                "reference": order.order_ref,
                "supplier_name": order.supplier.name if order.supplier else "-",
                "state": order.order_state,
            },
            "reservation_context": reservation_context,
            "lines": lines,
            "total_ht": f"{total_ht:.2f} EUR",
            "qr_code_data_uri": qr_code_data_uri,
        },
        fallback_filename=f"{order.order_ref}.pdf",
    )
    return send_file(
        pdf_stream,
        mimetype=PDF_MIMETYPE,
        as_attachment=True,
        download_name=filename,
    )

# ——————————————————————— Recherches de stocks ———————————————————————

@bp_stock.route("/search", methods=["GET"])
def search():
    """Page de recherche de stocks"""
    return render_page("stock_search")


@bp_stock.post("/search/wc-sync-catalog")
def wc_sync_catalog():
    """Déclenche la synchronisation globale du catalogue vers le Site Internet via app-back."""
    trigger_catalog_wc_sync()
    response = make_response("", 204)
    response.headers["HX-Trigger"] = "refreshTable"
    return response
