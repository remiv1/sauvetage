"""Application principale du frontend Flask pour Sauvetage"""

from datetime import datetime, timezone
from flask import Flask, jsonify, session, request, redirect, url_for, make_response
from app_front.utils.pages import render_page
from app_front.utils.router import is_allowed
from app_front.config.flask_conf import (
    DEBUG,
    LOG_LEVEL,
    FLASK_SECRET_KEY,
    BLUEPRINTS,
    sauv_logger,
)
from app_front.config.db_conf import DATABASE_URL, MONGODB_URL

# Création de l'application Flask
app = Flask(__name__)
app.secret_key = FLASK_SECRET_KEY
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
sauv_logger.log(level=LOG_LEVEL, message=log, action="app_start")


@app.before_request
def before_request():
    """Fonction exécutée avant chaque requête"""
    # Si l'utilisateur est déjà connecté, ne pas rediriger
    if "username" in session:
        return None
    # Vérifier si la page demandée est autorisée sans authentification
    if is_allowed(request.path):
        print("Accès à une page autorisée, aucune redirection nécessaire.")
        return None
    # Sinon, rediriger vers la page de connexion
    print(f"page demandée : {request.path} --> redirection vers login")
    return redirect(url_for("user.login"))


@app.after_request
def after_request(response):
    """Fonction exécutée après chaque requête"""
    path = request.path
    # Ignorer les fichiers statiques et les fragments HTMX
    if path.startswith("/static/") or "/htmx/" in path:
        return response
    method = request.method
    if method not in ("GET", "POST", "PUT", "PATCH", "DELETE"):
        return response
    sauv_logger.log(
        level=LOG_LEVEL,
        message=path,
        action=method,
        log_type="logs",
        user_id=session.get("username"),
        status_code=response.status_code,
        ip_address=request.remote_addr,
    )
    return response


@app.route("/", methods=["GET"])
def home():
    """Endpoint racine du frontend"""
    return render_page("home")


@app.route("/health", methods=["GET"])
def health():
    """Endpoint de santé pour load balancer"""
    return (
        jsonify(
            {
                "status": "healthy",
                "service": "sauvetage-frontend",
                "version": "1.0.0",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        ),
        200,
    )


@app.route("/ready", methods=["GET"])
def ready():
    """Endpoint de disponibilité (readiness check)"""
    return (
        jsonify(
            {
                "status": "ready",
                "service": "sauvetage-frontend",
                "version": "1.0.0",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        ),
        200,
    )


@app.errorhandler(404)
def not_found(_error: Exception):
    """Gestion des erreurs 404 avec code HTTP explicite"""
    payload = {
        "status": "error",
        "code": 404,
        "message": "Resource not found",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    return make_response(jsonify(payload), 404)


@app.errorhandler(500)
def internal_error(_error: Exception):
    """Gestion des erreurs 500 avec code HTTP explicite"""
    payload = {
        "status": "error",
        "code": 500,
        "message": "Internal server error",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    return make_response(jsonify(payload), 500)
