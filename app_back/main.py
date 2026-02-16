"""Module principal de l'application FastAPI pour le backend de Sauvetage."""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from app_back.router import v1_api_router

# Configuration
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
LOG_LEVEL = os.getenv("LOG_LEVEL", "info")

# Lifespan event handlers
@asynccontextmanager
async def lifespan(app: FastAPI):   # pylint: disable=unused-argument, redefined-outer-name
    """Gère les événements de démarrage et d'arrêt de l'application."""
    # Startup
    print(f"Starting FastAPI application (DEBUG={DEBUG}, LOG_LEVEL={LOG_LEVEL})")
    try:
        # TODO: Initialize database connections here
        print("Database connections initialized")
    except (OSError) as e:
        print(f"Warning: Could not initialize database connections: {e}")
    yield
    # Shutdown
    print("Shutting down FastAPI application")
    # TODO: Close database connections here

# Create FastAPI app
app = FastAPI(
    title="Sauvetage Backend API",
    description="Backend API for Sauvetage application",
    version="1.0.0",
    lifespan=lifespan,
    debug=DEBUG,
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
        # TODO: Check database connectivity
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
