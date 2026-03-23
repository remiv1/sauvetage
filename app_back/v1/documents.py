"""Module de routage pour la gestion des documents de l'application Sauvetage."""

import base64
from fastapi import APIRouter, HTTPException
from app_back.v1.schems.documents import DocumentSchema
from app_back.utils.documents import create_document_buffer

router = APIRouter(prefix="/documents", tags=["document"])

@router.post("/create",
             responses={
                 200: {"description": "Document créé avec succès."},
                 500: {"description": "Erreur lors de la création du document."}
             })
def create_document(payload: DocumentSchema):
    """Génère un PDF en mémoire et le renvoie à Flask."""
    try:
        pdf_bytes = create_document_buffer(
            template_name=payload.template,
            data=payload.data
        )

        # Encodage base64 pour transit JSON
        pdf_b64 = base64.b64encode(pdf_bytes).decode("utf-8")

        return {
            "status": "success",
            "filename": f"{payload.template}.pdf",
            "content": pdf_b64,
            "content_type": "application/pdf"
        }

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
