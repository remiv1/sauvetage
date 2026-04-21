"""Application principale du frontend Flask pour Sauvetage"""

from typing import Any
import logging
from datetime import datetime, timezone
from jinja2 import TemplateError
from flask import Flask, jsonify, session, request, redirect, url_for, make_response
from flask.typing import ResponseReturnValue
from app_front.utils.pages import render_page
from app_front.utils.router import is_allowed
from app_front.config.flask_conf import (
    DEBUG,
    LOG_LEVEL,
    FLASK_SECRET_KEY,
    BLUEPRINTS,
    setup_logging,
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
setup_logging()
logger = logging.getLogger("app_front")
logger.info(msg=log, extra={"level": LOG_LEVEL, "action": "app_start"})


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
    # Ignorer les fichiers statiques
    if path.startswith("/static/"):
        return response
    method = request.method
    if method not in ("GET", "POST", "PUT", "PATCH", "DELETE"):
        return response
    logger.info(
        msg=path,
        extra={
            "level": LOG_LEVEL,
            "action": method,
            "log_type": "logs",
            "user_id": session.get("username"),
            "status_code": response.status_code,
            "ip_address": request.remote_addr,
        },
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


@app.errorhandler(400)
@app.errorhandler(401)
@app.errorhandler(403)
@app.errorhandler(404)
@app.errorhandler(405)
def error_handler(_error: Any) -> ResponseReturnValue:   # pylint: disable=unused-argument
    """Gestion centralisée des erreurs HTTP.

    Pour les erreurs 4xx : log + rendu d'une page utilisateur agréable.
    Sinon : retourne un payload JSON de secours.
    """
    code = getattr(_error, "code", None)
    if not isinstance(code, int):
        code = 400

    logger.error(
        msg=request.path,
        extra={
            "level": LOG_LEVEL,
            "action": request.method,
            "log_type": "logs",
            "user_id": session.get("username"),
            "status_code": code,
            "ip_address": request.remote_addr,
        },
    )
    message = getattr(_error, "description", None) or str(_error)
    try:
        html = render_page("error/4xx", code=code, message=message)
        return html, int(code)
    except TemplateError:
        # fallback JSON si le template échoue
        pass    # pylint: disable=unnecessary-pass

    payload = {
        "status": "error",
        "code": code,
        "message": message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    return make_response(jsonify(payload), int(code))


@app.errorhandler(500)
@app.errorhandler(502)
@app.errorhandler(503)
@app.errorhandler(504)
def internal_error(_error: Any) -> ResponseReturnValue:
    """Gestion des erreurs 500 avec rendu HTML convivial ou JSON pour les requêtes XHR/HTMX."""
    logger.error(
        msg=f"Internal server error: {request.path}",
        extra={
            "level": LOG_LEVEL,
            "action": request.method,
            "log_type": "logs",
            "user_id": session.get("username"),
            "status_code": 500,
            "ip_address": request.remote_addr,
        }
    )

    # message lisible pour le template / JSON
    message = getattr(_error, "description", None) or str(_error) or "Internal server error"

    # Détecter les requêtes XHR / HTMX / Accept JSON
    is_htmx = request.headers.get("HX-Request") == "true"
    is_xhr = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    accepts_json = "application/json" in request.headers.get("Accept", "")

    if not (is_htmx or is_xhr or accepts_json):
        try:
            html = render_page("error/5xx", code=500, message=message)
            return html, 500
        except TemplateError:
            # si rendu échoue pour des erreurs de template, fallback en JSON
            pass    # pylint: disable=unnecessary-pass

    payload = {
        "status": "error",
        "code": 500,
        "message": message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    return make_response(jsonify(payload), 500)
