"""Blueprint pour les fonctionnalités d'administration"""

from flask import Blueprint, redirect, url_for, flash
from app_front.blueprints.admin.forms import FirstUserForm
from app_front.utils.pages import render_page
from app_front.blueprints.user.utils import create_user, check_no_users
from app_front.utils.decorators import permission_required, ADMIN, SUPER_ADMIN

bp_admin = Blueprint("admin", __name__, url_prefix="/admin")


@bp_admin.get("/")
@permission_required([ADMIN, SUPER_ADMIN], _and=False)
def index():
    """Route pour la page d'administration"""
    return render_page("admin_index")


@bp_admin.route("/first-user", methods=["GET", "POST"])
def create_first_user():
    """Route pour créer le premier utilisateur admin"""
    first_user = check_no_users()
    if first_user is False:
        return redirect(url_for("user.login"))
    form = FirstUserForm()
    if form.validate_on_submit():
        password = form.password.data
        confirm_password = form.confirm_password.data
        username = form.username.data
        email = form.email.data
        if (
            (password != confirm_password)
            or (password is None)
            or (username is None)
            or (email is None)
        ):
            message = "Les mots de passe ne correspondent pas."
            form.password.errors = list(form.password.errors) + [message]
            return redirect(url_for("admin.create_first_user"))
        ok = create_user(
            username=username, email=email, password=password, permissions="9"
        )
        if ok:
            message = f"Premier utilisateur '{username}' créé avec succès."
            flash(message, "success")
            return redirect(url_for("user.login"))
        message = "Une erreur est survenue lors de la création du premier utilisateur."
        flash(message, "danger")
    return render_page("register", form=form, first_user=first_user)
