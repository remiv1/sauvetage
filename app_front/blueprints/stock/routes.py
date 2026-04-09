"""Blueprint pour les fonctionnalités de gestion des stocks"""

from flask import Blueprint, flash, redirect, request, send_file, url_for
from app_front.utils.pages import render_page
from app_front.blueprints.stock.utils import (
    is_zero_price_items,
    get_zero_price_items,
    get_supplier_orders,
    get_order_by_id,
    create_order_in_db,
)
from app_front.blueprints.stock.forms import OrderInCreateForm
from app_front.utils.documents import build_qrcode_data_uri, create_pdf_from_template

bp_stock = Blueprint("stock", __name__, url_prefix="/stock")


@bp_stock.route("/", methods=["GET"])
def index():
    """Page d'accueil du module stocks"""
    has_zero_price_items = is_zero_price_items()
    return render_page("stock_index", has_zero_price_items=has_zero_price_items)


@bp_stock.route("/council", methods=["GET", "POST"])
def council():
    """Page de gestion de réconciliation des prix de stocks"""
    items_to_council = get_zero_price_items()
    return render_page("stock_council", items_to_council=items_to_council)


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
        line_total = float(line.qty_ordered or 0) * float(line.unit_price or 0)
        total_ht += line_total
        lines.append(
            {
                "article_name": line.general_object.name if line.general_object else f"Article #{line.general_object_id}",
                "quantity": int(line.qty_ordered or 0),
                "unit_price": f"{float(line.unit_price or 0):.2f} EUR",
                "vat_rate": f"{float(line.vat_rate or 0):.1f} %",
                "line_total_ht": f"{line_total:.2f} EUR",
            }
        )

    pdf_stream, filename = create_pdf_from_template(
        "pdf/supplier_order_slip.html",
        {
            "order": {
                "reference": order.order_ref,
                "external_ref": order.external_ref or "-",
                "supplier_name": order.supplier.name if order.supplier else "-",
                "state": order.order_state,
            },
            "lines": lines,
            "total_ht": f"{total_ht:.2f} EUR",
            "qr_code_data_uri": qr_code_data_uri,
        },
        fallback_filename=f"{order.order_ref}.pdf",
    )
    return send_file(
        pdf_stream,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename,
    )


@bp_stock.route("/orders/new", methods=["GET", "POST"])
def create_order():
    """Création d'une nouvelle commande fournisseur"""
    return render_page("stock_order")


@bp_stock.route("/returns/new", methods=["GET", "POST"])
def create_return():
    """Création d'un retour fournisseur"""
    return render_page("stock_order")


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
        line_total = float(line.qty_ordered or 0) * float(line.unit_price or 0)
        total_ht += line_total
        lines.append(
            {
                "article_name": line.general_object.name if line.general_object else f"Article #{line.general_object_id}",
                "quantity": int(line.qty_ordered or 0),
                "line_state": line.line_state,
                "unit_price": f"{float(line.unit_price or 0):.2f} EUR",
                "line_total_ht": f"{line_total:.2f} EUR",
            }
        )

    pdf_stream, filename = create_pdf_from_template(
        "pdf/reservation_slip.html",
        {
            "order": {
                "reference": order.order_ref,
                "supplier_name": order.supplier.name if order.supplier else "-",
                "state": order.order_state,
            },
            "lines": lines,
            "total_ht": f"{total_ht:.2f} EUR",
            "qr_code_data_uri": qr_code_data_uri,
        },
        fallback_filename=f"{order.order_ref}.pdf",
    )
    return send_file(
        pdf_stream,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename,
    )


@bp_stock.route("/search", methods=["GET"])
def search():
    """Page de recherche de stocks"""
    return render_page("stock_search")
