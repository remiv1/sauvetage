"""Application principale du frontend Flask pour Sauvetage"""

from datetime import datetime, timezone
from flask import Flask, jsonify, session, request, redirect, url_for, g
from app_front.utils.pages import render_page
from app_front.config.flask_conf import (
    DEBUG, LOG_LEVEL, FLASK_SECRET_KEY, BLUEPRINTS, sauv_logger)
from app_front.config.db_conf import get_main_session, DATABASE_URL, MONGODB_URL
from db_models.services.auth import AuthService
from db_models.repositories.user import UsersRepository

# Création de l'application Flask
app = Flask(__name__)
app.config["SECRET_KEY"] = FLASK_SECRET_KEY
app.config["DEBUG"] = DEBUG

# Enregistrement des blueprints
for bp in BLUEPRINTS:
    app.register_blueprint(bp)

log = f"""
[MAIN] Application Flask initialisée avec succès
[MAIN] Configuration :
- DEBUG: {DEBUG}
- LOG_LEVEL: {LOG_LEVEL}
- DATABASE_URL: {DATABASE_URL}
- MONGODB_URL: {MONGODB_URL}
- FLASK_SECRET_KEY: {'***'}
- BLUEPRINTS: {[bp.name for bp in BLUEPRINTS]}
"""
sauv_logger.log(level=LOG_LEVEL,
                message=log,
                action="app_start")

@app.before_request
def before_request():
    """Fonction exécutée avant chaque requête"""
    # Si l'utilisateur est déjà connecté
    g.db_session = get_main_session()
    user_repo = UsersRepository(g.db_session)
    auth_service = AuthService(user_repo=user_repo)
    if 'user_id' in session:
        # Vérifier la validité de la session
        user = auth_service.validate_session()
        if not user:
            session.clear()  # Invalider la session si l'utilisateur n'est plus valide
    if request.path.endswith("/login"):
        # Si c'est une tentative de connexion, on ne fait rien ici
        return None
    if request.path.startswith("/static/"):
        # Ignorer les requêtes pour les ressources statiques
        return None
    # Cas de l'utilisateur non loggué
    return redirect(url_for("user.login"))

@app.after_request
def after_request(response):
    """Fonction exécutée après chaque requête"""
    sauv_logger.log(
        level=LOG_LEVEL,
        message=f"Requête {request.method} {request.path} - Status: {response.status_code}",
        action="request_log"
    )
    return response

@app.route("/")
def root():
    """Endpoint racine du frontend"""
    return render_page("default")


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
