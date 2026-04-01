"""Routes HTMX pour le dashboard des logs (admin et super-admin)."""

from flask import Blueprint, render_template, request
from app_front.utils.decorators import permission_required, ADMIN, SUPER_ADMIN
from app_front.blueprints.admin.utils import get_logs_stats, get_logs_recent

bp_admin_logs = Blueprint("admin_logs", __name__, url_prefix="/admin/htmx/logs")

LOGS_STATS = "htmx_templates/admin/logs/stats.html"
LOGS_TABLE = "htmx_templates/admin/logs/table.html"

LOG_TYPES = ["users", "logs", "clients", "métiers"]
LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


@bp_admin_logs.get("/stats")
@permission_required([ADMIN, SUPER_ADMIN], _and=False)
def logs_stats():
    """Fragment HTMX — statistiques de logs par type et niveau."""
    year_str = request.args.get("year", "").strip()
    year = int(year_str) if year_str.isdigit() else None
    stats = get_logs_stats(year=year)
    return render_template(LOGS_STATS, **stats, log_types=LOG_TYPES)


@bp_admin_logs.get("/table")
@permission_required([ADMIN, SUPER_ADMIN], _and=False)
def logs_table():
    """Fragment HTMX — tableau paginé des logs récents."""
    log_type = request.args.get("log_type", "logs").strip()
    if log_type not in LOG_TYPES:
        log_type = "logs"
    level = request.args.get("level", "").strip() or None
    user_id = request.args.get("user_id", "").strip() or None
    method = request.args.get("method", "").strip() or None
    status = request.args.get("status", "").strip() or None
    page_str = request.args.get("page", "1").strip()
    page = max(1, int(page_str)) if page_str.isdigit() else 1
    year_str = request.args.get("year", "").strip()
    year = int(year_str) if year_str.isdigit() else None

    result = get_logs_recent(
        log_type=log_type,
        level=level,
        user_id=user_id,
        method=method,
        status=status,
        page=page,
        year=year,
    )
    return render_template(
        LOGS_TABLE,
        **result,
        log_type=log_type,
        log_types=LOG_TYPES,
        log_levels=LOG_LEVELS,
        selected_level=level or "",
        selected_method=method or "",
        selected_status=status or "",
    )
