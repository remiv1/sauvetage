"""Application principale du frontend Flask pour Sauvetage"""

import os
from datetime import datetime, timezone

from flask import Flask, jsonify

# Configuration
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
LOG_LEVEL = os.getenv("LOG_LEVEL", "info").upper()
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://app:pwd@db-main:5432/sauvetage_main"
)
MONGODB_URL = os.getenv(
    "MONGODB_URL",
    "mongodb://app:pwd@db-logs:27017/sauvetage_logs"
)
FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-secret-key-change-in-production")

# Création de l'application Flask
app = Flask(__name__)
app.config["SECRET_KEY"] = FLASK_SECRET_KEY
app.config["DEBUG"] = DEBUG

print("[MAIN] Configuration Flask chargée")
print(f"[MAIN] DEBUG={DEBUG}")
print(f"[MAIN] LOG_LEVEL={LOG_LEVEL}")
print(f"[MAIN] DATABASE_URL={DATABASE_URL}")
print(f"[MAIN] MONGODB_URL={MONGODB_URL}")


@app.route("/")
def root():
    """Endpoint racine du frontend"""
    return jsonify({
        "status": "ok",
        "message": "Sauvetage Frontend API",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat()
    })


@app.route("/health")
def health():
    """Endpoint de santé pour load balancer"""
    return jsonify({
        "status": "healthy",
        "service": "sauvetage-frontend",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }), 200


@app.route("/ready")
def ready():
    """Endpoint de disponibilité (readiness check)"""
    return jsonify({
        "status": "ready",
        "service": "sauvetage-frontend",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }), 200


@app.errorhandler(404)
def not_found(_error: Exception):
    """Gestion des erreurs 404"""
    return jsonify({
        "status": "error",
        "code": 404,
        "message": "Resource not found",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }), 404


@app.errorhandler(500)
def internal_error(_error: Exception):
    """Gestion des erreurs 500"""
    return jsonify({
        "status": "error",
        "code": 500,
        "message": "Internal server error",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }), 500


if __name__ == "__main__":
    # Développement uniquement (gunicorn utilisé en production)
    app.run(host="0.0.0.0", port=5000, debug=DEBUG)
