"""Module contenant les routes liées à l'utilisateur :
    - /login : Route pour la connexion d'un utilisateur existant.
    - /logout : Route pour la déconnexion de l'utilisateur connecté.
    - /user/create : Route pour la création d'un nouvel utilisateur.
    - /user/<int:id>/view : Route pour afficher les détails d'un utilisateur spécifique.
    - /user/<int:id>/edit : Route pour éditer les informations d'un utilisateur spécifique.
    - /user/<int:id>/delete : Route pour supprimer un utilisateur spécifique.
"""

from urllib.parse import unquote
from flask import Blueprint, redirect, url_for, flash, session
from app_front.blueprints.user.forms import (
    LoginForm, UserCreateForm, UserPasswordChangeForm, UserEditForm
    )
from app_front.blueprints.user.utils import (
    check_no_users, log_user, create_user, change_password, modify_user, user_search
    )
from app_front.utils.decorators import permission_required, ADMIN, SUPER_ADMIN, ALL
from app_front.utils.pages import render_page

bp_user = Blueprint('user', __name__, url_prefix='/user')

@bp_user.route('/login', methods=['GET', 'POST'])
def login():
    """Route pour la connexion d'un utilisateur existant."""
    # Initialiser le service d'authentification avec le repository utilisateur
    no_users = check_no_users()

    # Récupération du formulaire de connexion
    form = LoginForm()

    # Traiter la soumission du formulaire
    if form.validate_on_submit():
        # Récupérer l'utilisateur par nom d'utilisateur
        user_input = form.username.data or ""
        pwd_input = form.password.data or ""
        data = log_user(user_input, pwd_input)
        success = data.get("valid", False)
        username = data.get("username", None)
        email = data.get("email", None)
        permissions = data.get("permissions", [])
        message = "Une erreur inconnue du développeur est survenue."
        error = data.get("error", message)
        if not success:
            flash(error, 'danger')
        else:
            session['username'] = username
            session['email'] = email
            session['permissions'] = permissions
            flash('Connexion réussie.', 'success')
            return redirect(url_for('dashboard.index'))

    # Afficher le formulaire de connexion
    return render_page('login', form=form, first_user=no_users)

@permission_required(SUPER_ADMIN)
@bp_user.route('/register', methods=['GET', 'POST'])
def register():
    """Route pour la création d'un nouvel utilisateur."""
    form = UserCreateForm()

    if form.validate_on_submit():
        user_input = form.username.data or ""
        email_input = form.email.data or ""
        pwd_input = form.password.data or ""
        permissions_input = form.permissions.data or []
        create_user(
            username=user_input,
            email=email_input,
            password=pwd_input,
            permissions="".join(permissions_input)
            )
        flash(f'Utilisateur {user_input} créé avec succès.', 'success')
        return redirect(url_for('user.login'))
    return render_page('register', form=form)

@permission_required(ALL, _and=False)
@bp_user.route('/logout')
def logout():
    """Route pour la déconnexion de l'utilisateur connecté."""
    session.clear()
    flash('Déconnexion réussie.', 'success')
    return redirect(url_for('user.login'))

@permission_required(ALL, _and=False)
@bp_user.route('/change-password/<username>', methods=['GET', 'POST'])
def chg_pwd(username):
    """Route pour changer le mot de passe d'un utilisateur spécifique."""
    form = UserPasswordChangeForm()
    username = unquote(username)
    if form.validate_on_submit():
        old_password = form.old_password.data
        new_password = form.new_password.data
        new_password_confirm = form.new_password_confirm.data
        if (new_password != new_password_confirm) \
            or (new_password is None) \
            or (old_password is None) \
            or (new_password.strip() == ""):
            message = "Les nouveaux mots de passe ne correspondent pas ou sont vides."
            flash(message, 'danger')
            return render_page('change_password', form=form, username=username)
        try:
            ok = change_password(
                        username=username,
                        old_password=old_password,
                        new_password=new_password
                        )
            if not ok:
                message = "Erreur inconnue du développeur lors du changement de mot de passe."
                flash(message, 'danger')
                return render_page('change_password', form=form, username=username)
            flash('Mot de passe changé avec succès.', 'success')
            return redirect(url_for('home'))
        except (ValueError, KeyError) as e:
            flash(str(e), 'danger')
    return render_page('change_password', form=form, username=username)

@permission_required([ADMIN, SUPER_ADMIN], _and=False)
@bp_user.route('/modify/<username>', methods=['GET', 'POST'])
def modify(username):
    """Route pour éditer les informations d'un utilisateur spécifique."""
    form = UserEditForm()
    username = unquote(username)
    user = user_search(username=username)
    if form.validate_on_submit():
        email_input = form.email.data
        permissions_input = form.permissions.data or []
        if email_input is None or email_input.strip() == "":
            flash("L'email ne peut pas être vide.", 'danger')
            return render_page('modify', form=form, user=user)
        modify_user(
            username=username,
            email=email_input,
            permissions="".join(permissions_input)
        )
        flash(f'Utilisateur {username} mis à jour avec succès.', 'success')
        return redirect(url_for('user.modify', username=username, form=form))
    form.username.data = user.get("username", "")
    form.email.data = user.get("email", "")
    form.permissions.data = list(user.get("permissions", ""))
    return render_page('modify', form=form, user=user)
