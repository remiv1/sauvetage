"""Blueprint pour les fonctionnalités d'administration"""

import requests
from flask import Blueprint, redirect, url_for, flash
from app_front.blueprints.admin.forms import FirstUserForm
from app_front.config import API_URL
from app_front.utils.pages import render_page

bp_admin = Blueprint("admin", __name__, url_prefix="/admin")

@bp_admin.route("/first-user", methods=["GET", "POST"])
def create_first_user():
    """Route pour créer le premier utilisateur admin"""
    no_users_str = f"{API_URL}/users/no-user"
    first_user = requests.get(no_users_str, timeout=10).json().get("exists", False)
    print(f"First user exists: {first_user}")
    form = FirstUserForm()
    if first_user is False:
        return redirect(url_for("user.login"))
    if form.validate_on_submit():
        password = form.password.data
        confirm_password = form.confirm_password.data
        if password != confirm_password:
            message = "Les mots de passe ne correspondent pas."
            form.password.errors = list(form.password.errors) + [message]
            return redirect(url_for("admin.create_first_user"))
        user = {
            "username": form.username.data,
            "email": form.email.data,
            "password": form.password.data,
            "permissions": "9"
        }
        response = requests.post(f"{API_URL}/users/create",
                                 json=user,
                                 timeout=10)
        ok = response.json().get("valid", False)
        message = response.json().get("error", "Erreur lors de la création de l'utilisateur.")
        if response.status_code // 100 == 2 and ok:
            print(response.json())
            flash(message, "success")
            return redirect(url_for("user.login"))
        else:
            form.username.errors = list(form.username.errors) + [message]
            return render_page('register', form=form, first_user=first_user)
    return render_page('register', form=form, first_user=first_user)
