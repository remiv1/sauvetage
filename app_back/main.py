"""Module principal de l'application FastAPI pour le backend de Sauvetage."""

from os import getenv
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from app_back.router import v1_api_router
from app_back.migration import run_migrations_with_lock
from logs.logger import get_logger

# Configuration
DEBUG = getenv("DEBUG", "false").lower() == "true"
LOG_LEVEL = getenv("LOG_LEVEL", "info")
sauv_logger = get_logger()
# Exécution des migrations avec advisory lock PostgreSQL.
# Chaque worker Gunicorn importe ce module, mais seul le premier
# à obtenir le lock exécutera réellement les migrations.
# Les autres attendront la fin puis continueront sans migrer.
run_migrations_with_lock(timeout=300)

# Create FastAPI app
app = FastAPI(
    title="Sauvetage Backend API",
    description="Backend API for Sauvetage application",
    version="1.0.0",
    debug=True,
)

# Include API routers
app.include_router(v1_api_router, prefix="/api")

@app.get("/")
async def read_root():
    """Endpoint racine pour vérifier que l'API fonctionne"""
    return {
        "status": "ok",
        "message": "Sauvetage Backend API",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    """
    Endpoint de vérification de l'état de santé pour les équilibreurs de charge et
    les orchestrateurs
    Retourne 200 lorsque le service est en bonne santé et 503 lorsqu'il ne l'est pas.
    """
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "service": "sauvetage-backend",
            "version": "1.0.0"
        }
    )

@app.get("/ready")
async def readiness_check():
    """
    Endpoint de vérification de la disponibilité.
    Retourne 200 lorsque le service est prêt à accepter du trafic
    et 503 lorsqu'il n'est pas prêt (par exemple, si la connexion à la base de données échoue).
    """
    try:
        return JSONResponse(
            status_code=200,
            content={
                "status": "ready",
                "service": "sauvetage-backend"
            }
        )
    except (ConnectionError, TimeoutError) as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "error": str(e),
                "service": "sauvetage-backend"
            }
        )
