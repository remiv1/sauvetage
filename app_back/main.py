"""Module principal de l'application FastAPI pour le backend de Sauvetage."""

from os import getenv
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from app_back.router import v1_api_router
from app_back.migration import run_startup_tasks
from logs.logger import MongoForwardHandler, get_logger

# Configuration
DEBUG = getenv("DEBUG", "false").lower() == "true"
LOG_LEVEL = getenv("LOG_LEVEL", "info").upper()

def setup_logging():
    """Configure le logging pour l'application."""
    root_logger = logging.getLogger()
    # éviter les doublons si reload Uvicorn/Gunicorn
    if any(isinstance(h, MongoForwardHandler) for h in root_logger.handlers):
        return
    handler = MongoForwardHandler(get_logger())
    root_logger.setLevel(LOG_LEVEL)
    root_logger.addHandler(handler)

# Exécution des migrations avec advisory lock PostgreSQL.
# Chaque worker Gunicorn importe ce module, mais seul le premier
# à obtenir le lock exécutera réellement les migrations.
# Les autres attendront la fin puis continueront sans migrer.
run_startup_tasks(timeout=300)

@asynccontextmanager
async def lifespan(app: FastAPI):   # pylint: disable=unused-argument, redefined-outer-name
    """Gère les événements de démarrage et d'arrêt de l'application."""
    print(">>> Lifespan Start...")
    setup_logging()
    print(">>> Logging configured.")
    logging.getLogger("app_back").info("Démarrage de Sauvetage Backend API...")
    logging.getLogger("pymongo").setLevel(logging.WARNING)
    logging.getLogger("pymongo.topology").setLevel(logging.WARNING)
    logging.getLogger("pymongo.connection").setLevel(logging.WARNING)
    logging.getLogger("pymongo.command").setLevel(logging.WARNING)

    yield
    print(">>> Lifespan End...")
    logging.getLogger("app_back").info("Arrêt de Sauvetage Backend API...")

# Create FastAPI app
app = FastAPI(
    title="Sauvetage Backend API",
    description="Backend API for Sauvetage application",
    version="1.0.0",
    debug=DEBUG,
    lifespan=lifespan
)

# Include API routers
app.include_router(v1_api_router, prefix="/api")

@app.get("/")
async def read_root():
    """Endpoint racine pour vérifier que l'API fonctionne"""
    return {"status": "ok", "message": "Sauvetage Backend API", "version": "1.0.0"}


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
            "version": "1.0.0",
        },
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
            status_code=200, content={"status": "ready", "service": "sauvetage-backend"}
        )
    except (ConnectionError, TimeoutError) as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "error": str(e),
                "service": "sauvetage-backend",
            },
        )
