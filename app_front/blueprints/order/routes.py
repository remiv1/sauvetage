"""Blueprint pour les fonctionnalités des commandes clients"""

from flask import Blueprint, send_file, url_for
from app_front.utils.pages import render_page
from app_front.blueprints.order.utils import get_order_by_id
from app_front.utils.documents import build_qrcode_data_uri, create_pdf_from_template

bp_order = Blueprint("order", __name__, url_prefix="/order")
ORDER_NOT_FOUND = "<p>Commande introuvable.</p>"


@bp_order.get("/")
def index():
    """Page de gestion des commandes avec liste paginée et filtres."""
    return render_page("order_index")

@bp_order.get("/view/<int:order_id>")
def order_view(order_id: int):
    """Page complète de consultation d'une commande."""
    order = get_order_by_id(order_id)
    if order is None:
        return ORDER_NOT_FOUND, 404
    # Redirection vers la page complète (pas une modale)
    return render_page("order_view", order=order)


def _format_address(address: dict | None) -> str:
    """Formate une adresse lisible pour le bon PDF."""
    if not address:
        return "-"
    line1 = address.get("address_line1") or ""
    line2 = address.get("address_line2") or ""
    postal = address.get("postal_code") or ""
    city = address.get("city") or ""
    chunks = [line1, line2, f"{postal} {city}".strip()]
    return ", ".join([chunk for chunk in chunks if chunk]) or "-"


@bp_order.get("/view/<int:order_id>/slip.pdf")
def order_download_slip(order_id: int):
    """Télécharge le bon de commande client (PDF)."""
    order = get_order_by_id(order_id)
    if order is None:
        return ORDER_NOT_FOUND, 404

    open_url = url_for("order.order_view", order_id=order_id, modal="view", _external=True)
    qr_code_data_uri = build_qrcode_data_uri(open_url)

    lines = []
    total_ht = 0.0
    for line in order.get("lines", []):
        total_ht += float(line.get("line_total_ht") or 0)
        lines.append(
            {
                "article_name": line.get("article_name") or "-",
                "quantity": line.get("quantity") or 0,
                "unit_price": f"{float(line.get('unit_price') or 0):.2f} EUR",
                "vat_rate": f"{float(line.get('vat_rate') or 0):.1f} %",
                "line_total_ht": f"{float(line.get('line_total_ht') or 0):.2f} EUR",
            }
        )

    pdf_stream, filename = create_pdf_from_template(
        "pdf/customer_order_slip.html",
        {
            "order": {
                "reference": order.get("reference") or f"CMD-{order_id}",
                "created_at": order.get("created_at") or "-",
                "customer_name": order.get("customer_name") or "-",
                "status_label": order.get("status_label") or "-",
                "invoice_address": _format_address(order.get("invoice_address")),
                "delivery_address": _format_address(order.get("delivery_address")),
            },
            "lines": lines,
            "total_ht": f"{total_ht:.2f} EUR",
            "qr_code_data_uri": qr_code_data_uri,
        },
        fallback_filename=f"{order.get('reference', order_id)}.pdf",
        filename=f"{order.get('reference', order_id)}.pdf",
    )
    return send_file(
        pdf_stream,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename,
    )
