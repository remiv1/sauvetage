"""Routes HTMX pour la gestion des utilisateurs (admin — super-admin uniquement)."""

import json
from flask import Blueprint, render_template, request, make_response, flash
from app_front.utils.decorators import permission_required, SUPER_ADMIN
from app_front.blueprints.admin.forms import UserCreateAdminForm, UserEditPermissionsForm
from app_front.blueprints.admin.utils import (
    list_users_paginated,
    toggle_user_lock,
    toggle_user_active,
)
from app_front.blueprints.user.utils import create_user, modify_user

bp_admin_users = Blueprint("admin_users", __name__, url_prefix="/admin/htmx/users")

USERS_TABLE = "htmx_templates/admin/users/table.html"
USERS_CREATE_MODAL = "htmx_templates/admin/users/create_modal.html"
USERS_EDIT_MODAL = "htmx_templates/admin/users/edit_modal.html"
USERS_TOGGLE_MODAL = "htmx_templates/admin/users/toggle_modal.html"
USER_NOT_FOUND = "<p>Utilisateur introuvable.</p>"

# Mapping lisible des permissions
PERMISSION_LABELS = {
    "1": "Admin",
    "2": "Comptable",
    "3": "Commercial",
    "4": "Logistique",
    "5": "Support",
    "6": "Informatique",
    "7": "RH",
    "8": "Direction",
    "9": "Super Admin",
}


@bp_admin_users.get("/table")
@permission_required(SUPER_ADMIN)
def users_table():
    """Tableau paginé et filtré des utilisateurs."""
    username = request.args.get("username", "").strip() or None
    email = request.args.get("email", "").strip() or None
    permissions = request.args.get("permissions", "").strip() or None
    is_active_str = request.args.get("is_active", "").strip()
    is_locked_str = request.args.get("is_locked", "").strip()
    is_active = True if is_active_str == "true" else (False if is_active_str == "false" else None)
    is_locked = True if is_locked_str == "true" else (False if is_locked_str == "false" else None)
    page_str = request.args.get("page", "1").strip()
    page = max(1, int(page_str)) if page_str.isdigit() else 1

    try:
        result = list_users_paginated(
            username=username,
            email=email,
            permissions=permissions,
            is_active=is_active,
            is_locked=is_locked,
            page=page,
        )
    except Exception:
        result = {"items": [], "total": 0, "page": 1, "per_page": 20}

    return render_template(USERS_TABLE, **result, permission_labels=PERMISSION_LABELS)


@bp_admin_users.get("/create-form")
@permission_required(SUPER_ADMIN)
def users_create_form():
    """Modale de création d'un utilisateur."""
    form = UserCreateAdminForm()
    return render_template(USERS_CREATE_MODAL, form=form)


@bp_admin_users.post("/create")
@permission_required(SUPER_ADMIN)
def users_create():
    """Crée un utilisateur depuis l'admin."""
    form = UserCreateAdminForm()
    if form.validate_on_submit():
        permissions_str = "".join(sorted(form.permissions.data or []))
        try:
            create_user(
                username=form.username.data,
                email=form.email.data,
                password=form.password.data,
                permissions=permissions_str,
            )
        except Exception as exc:
            form.username.errors = list(form.username.errors) + [str(exc)]
            return render_template(USERS_CREATE_MODAL, form=form), 422
        response = make_response("", 200)
        response.headers["HX-Trigger"] = json.dumps({"user:created": True})
        return response
    return render_template(USERS_CREATE_MODAL, form=form), 422


@bp_admin_users.get("/edit/<username>")
@permission_required(SUPER_ADMIN)
def users_edit_form(username: str):
    """Modale d'édition des permissions d'un utilisateur."""
    from app_front.blueprints.user.utils import user_search
    try:
        user_data = user_search(username)
    except Exception:
        return USER_NOT_FOUND, 404
    if not user_data.get("valid"):
        return USER_NOT_FOUND, 404

    form = UserEditPermissionsForm()
    form.email.data = user_data.get("email", "")
    current_perms = list(user_data.get("permissions", "") or "")
    form.permissions.data = current_perms
    return render_template(USERS_EDIT_MODAL, form=form, user=user_data, permission_labels=PERMISSION_LABELS)


@bp_admin_users.post("/edit/<username>")
@permission_required(SUPER_ADMIN)
def users_edit_submit(username: str):
    """Traite la modification des permissions d'un utilisateur."""
    form = UserEditPermissionsForm()
    if form.validate_on_submit():
        permissions_str = "".join(sorted(form.permissions.data or []))
        try:
            modify_user(
                username=username,
                email=form.email.data,
                permissions=permissions_str,
            )
        except Exception as exc:
            form.email.errors = list(form.email.errors) + [str(exc)]
            return render_template(USERS_EDIT_MODAL, form=form, user={"username": username}, permission_labels=PERMISSION_LABELS), 422
        response = make_response("", 200)
        response.headers["HX-Trigger"] = json.dumps({"user:updated": True})
        return response
    return render_template(USERS_EDIT_MODAL, form=form, user={"username": username}, permission_labels=PERMISSION_LABELS), 422


@bp_admin_users.get("/toggle-modal/<username>/<action>")
@permission_required(SUPER_ADMIN)
def users_toggle_modal(username: str, action: str):
    """Modale de confirmation de toggle lock ou active."""
    if action not in ("lock", "active"):
        return "<p>Action invalide.</p>", 400
    return render_template(USERS_TOGGLE_MODAL, username=username, action=action)


@bp_admin_users.post("/toggle-lock/<username>")
@permission_required(SUPER_ADMIN)
def users_toggle_lock(username: str):
    """Bascule le verrou d'un utilisateur."""
    try:
        toggle_user_lock(username)
    except Exception as exc:
        return str(exc), 500
    response = make_response("", 200)
    response.headers["HX-Trigger"] = json.dumps({"user:updated": True})
    return response


@bp_admin_users.post("/toggle-active/<username>")
@permission_required(SUPER_ADMIN)
def users_toggle_active(username: str):
    """Bascule le statut actif d'un utilisateur."""
    try:
        toggle_user_active(username)
    except Exception as exc:
        return str(exc), 500
    response = make_response("", 200)
    response.headers["HX-Trigger"] = json.dumps({"user:updated": True})
    return response
