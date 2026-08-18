"""Tests pour la route API de création de documents."""

from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app_back.v1.documents import create_document
from app_back.v1.schems.documents import DocumentSchema


def test_create_document_logs_exception_and_raises_500() -> None:
    """Une erreur de génération doit être logguée avant d'être renvoyée en 500."""
    payload = DocumentSchema(
        template="pdf/customer_order_slip.html",
        data={"order": {"reference": "CMD-1"}},
        base_url="http://localhost",
        filename="cmd-1.pdf",
    )

    with patch("app_back.v1.documents.create_document_buffer", side_effect=RuntimeError("boom")):
        with patch("app_back.v1.documents.logger.exception") as mock_logger:
            with pytest.raises(HTTPException) as exc_info:
                create_document(payload)

    assert exc_info.value.status_code == 500
    mock_logger.assert_called_once()
