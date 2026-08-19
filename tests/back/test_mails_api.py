"""Tests des routes et utilitaires d'envoi des e-mails."""

from datetime import datetime
from contextlib import nullcontext
from types import SimpleNamespace
from typing import cast
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app_back.v1.mails import routes
from app_back.v1.mails.utils import build_supplier_order_mail, send_mail_payload
from app_back.v1.schems.mails import AttachmentSchema, MailSchema, SupplierOrderMailSchema
from db_models.objects.stocks import OrderIn


def _mail_payload(attachments: list[AttachmentSchema] | None = None) -> MailSchema:
    """Construit un message minimal valable pour les tests."""
    return MailSchema(
        to=["fournisseur@example.com"],
        subject="Commande CMD-1",
        template="emails/purchase_order_email.html",
        data={},
        attachments=attachments,
    )


def test_send_mail_payload_returns_smtp_acceptance() -> None:
    """Le relais ayant accepté le message doit produire le statut métier attendu."""
    smtp_result = {
        "status": "accepted_by_smtp",
        "message": "Accepté par le relais SMTP.",
    }
    with patch("app_back.v1.mails.utils.send_mail", return_value=smtp_result) as mock_send:
        result = send_mail_payload(_mail_payload(), "le test")

    assert result["status"] == "accepted_by_smtp"
    assert result["message"] == "Accepté par le relais SMTP."
    mock_send.assert_called_once()


def test_send_mail_payload_rejects_invalid_base64_attachment() -> None:
    """Une pièce jointe mal encodée doit être refusée avant l'appel SMTP."""
    payload = _mail_payload(
        [
            AttachmentSchema(
                filename="commande.pdf",
                content="base64-invalide!",
                content_type="application/pdf",
            )
        ]
    )

    with patch("app_back.v1.mails.utils.send_mail") as mock_send:
        with pytest.raises(HTTPException) as exc_info:
            send_mail_payload(payload, "le test")

    assert exc_info.value.status_code == 400
    mock_send.assert_not_called()


def test_send_mail_payload_returns_502_on_smtp_error() -> None:
    """Une indisponibilité du relais SMTP doit être exposée en erreur 502."""
    payload = _mail_payload()
    with patch(
        "app_back.v1.mails.utils.send_mail",
        side_effect=OSError("Relais indisponible"),
    ):
        with pytest.raises(HTTPException) as exc_info:
            send_mail_payload(payload, "le test")

    assert exc_info.value.status_code == 502


def test_build_supplier_order_mail_returns_500_when_pdf_generation_fails() -> None:
    """Une erreur de génération PDF doit empêcher l'envoi avec une erreur 500."""
    order = cast(
        OrderIn,
        SimpleNamespace(
            id=1,
            supplier=SimpleNamespace(
                contact_email="fournisseur@example.com",
                name="Fournisseur",
            ),
            order_ref="CMD-1",
            external_ref=None,
            order_state="draft",
            orderin_lines=[],
            created_at=None,
        ),
    )
    payload = SupplierOrderMailSchema(order_id=1)

    with patch(
        "app_back.v1.mails.utils.create_document_buffer",
        side_effect=RuntimeError("PDF indisponible"),
    ):
        with pytest.raises(HTTPException) as exc_info:
            build_supplier_order_mail(order, payload)

    assert exc_info.value.status_code == 500


def test_build_supplier_order_mail_uses_company_config_and_order_date() -> None:
    """
    Le PDF et le mail doivent refléter la vraie configuration entreprise et la date de commande.
    """
    order = cast(
        OrderIn,
        SimpleNamespace(
            id=1,
            supplier=SimpleNamespace(
                contact_email="fournisseur@example.com",
                name="Fournisseur Exemple",
            ),
            order_ref="CMD-1",
            external_ref="EXT-42",
            order_state="draft",
            orderin_lines=[],
        ),
    )
    payload = SupplierOrderMailSchema(order_id=1)

    with patch(
        "app_back.v1.mails.utils.create_document_buffer",
        return_value=b"%PDF-1.4",
    ) as mock_create_document_buffer:
        mail, _ = build_supplier_order_mail(order, payload)

    assert mail.data["commande"]["date"] == datetime.now().strftime("%d/%m/%Y")
    assert mail.data["librairie"]["nom"] == (
        "TORRESANI CECILE (EDITIONS SAUVETAGE)"
    )
    assert mock_create_document_buffer.call_args.kwargs["data"]["internal"] is False
    assert mock_create_document_buffer.call_args.kwargs["data"]["company"]["name"] == (
        "TORRESANI CECILE (EDITIONS SAUVETAGE)"
    )


def test_send_supplier_order_mail_returns_404_when_order_is_missing() -> None:
    """Une commande inexistante doit renvoyer une erreur HTTP 404."""
    session = SimpleNamespace(get=lambda _model, _order_id: None)
    payload = SupplierOrderMailSchema(order_id=999)

    with patch(
        "app_back.v1.mails.routes.config.main_session_ctx",
        return_value=nullcontext(session),
    ):
        with pytest.raises(HTTPException) as exc_info:
            routes.send_supplier_order_mail(payload)

    assert exc_info.value.status_code == 404
