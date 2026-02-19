"""Module contenant les routes liées à l'utilisateur :
    - /login : Route pour la connexion d'un utilisateur existant.
    - /logout : Route pour la déconnexion de l'utilisateur connecté.
    - /user/create : Route pour la création d'un nouvel utilisateur.
    - /user/<int:id>/view : Route pour afficher les détails d'un utilisateur spécifique.
    - /user/<int:id>/edit : Route pour éditer les informations d'un utilisateur spécifique.
    - /user/<int:id>/delete : Route pour supprimer un utilisateur spécifique.
"""

import os
import requests
from flask import Blueprint, redirect, url_for, flash, session
from app_front.blueprints.user.forms import LoginForm, UserCreateForm
from app_front.utils.pages import render_page

bp_user = Blueprint('user', __name__, url_prefix='/user')
API_URL = os.getenv('API_URL', 'http://app-back:8000/api/v1')

@bp_user.route('/login', methods=['GET', 'POST'])
def login():
    """Route pour la connexion d'un utilisateur existant."""
    # Initialiser le service d'authentification avec le repository utilisateur
    no_users_str = f"{API_URL}/users/no-user"
    no_users = requests.get(no_users_str, timeout=10).json().get("exists", False)

    # Récupération du formulaire de connexion
    form = LoginForm()

    # Traiter la soumission du formulaire
    if form.validate_on_submit():
        # Récupérer l'utilisateur par nom d'utilisateur
        user_input = form.username.data or ""
        pwd_input = form.password.data or ""
        response = requests.post(f"{API_URL}/users/login/{user_input}/{pwd_input}", timeout=10)
        data = response.json()
        success = data.get("valid", False)
        username = data.get("username", None)
        mail = data.get("mail", None)
        permissions = data.get("permissions", [])
        error = data.get("error", None)
        if not success:
            flash(error, 'danger')
        else:
            session['username'] = username
            session['mail'] = mail
            session['permissions'] = permissions
            flash('Connexion réussie.', 'success')
            return redirect(url_for('home'))

    # Afficher le formulaire de connexion
    return render_page('login', form=form, first_user=no_users)

@bp_user.route('/register', methods=['GET', 'POST'])
def register():
    """Route pour la création d'un nouvel utilisateur."""
    form = UserCreateForm()

    if form.validate_on_submit():
        user_input = form.username.data or ""
        mail_input = form.mail.data or ""
        pwd_input = form.password.data or ""
        permissions_input = form.permissions.data or []
        user = {
            "username": user_input,
            "mail": mail_input,
            "password": pwd_input,
            "permissions": "".join(permissions_input)
        }
        response = requests.post(f"{API_URL}/users/create", json=user, timeout=10)
        if response.status_code != 200:
            flash(f"Erreur lors de la création de l'utilisateur : {response.text}", 'danger')
            return render_page('register', form=form)
        flash(f'Utilisateur {user["username"]} créé avec succès.', 'success')
        return redirect(url_for('user.login'))
    return render_page('register', form=form)
