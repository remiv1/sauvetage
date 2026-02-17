"""Module contenant les routes liées à l'utilisateur :
    - /login : Route pour la connexion d'un utilisateur existant.
    - /logout : Route pour la déconnexion de l'utilisateur connecté.
    - /user/create : Route pour la création d'un nouvel utilisateur.
    - /user/<int:id>/view : Route pour afficher les détails d'un utilisateur spécifique.
    - /user/<int:id>/edit : Route pour éditer les informations d'un utilisateur spécifique.
    - /user/<int:id>/delete : Route pour supprimer un utilisateur spécifique.
"""

from flask import Blueprint, render_template, redirect, url_for, flash
from app_front.blueprints.user.forms import LoginForm
from db_models.repositories.user import UsersRepository
from db_models.services.auth import AuthService

bp_user = Blueprint('user', __name__, url_prefix='/user')

@bp_user.route('/login', methods=['GET', 'POST'])
def login():
    """Route pour la connexion d'un utilisateur existant."""
    # Initialiser le service d'authentification avec le repository utilisateur
    user_obj = UsersRepository()
    auth_service = AuthService(user_obj)

    # Récupération du formulaire de connexion
    form = LoginForm()

    # Traiter la soumission du formulaire
    if form.validate_on_submit():
        # Récupérer l'utilisateur par nom d'utilisateur
        user_input = form.username.data or ""
        pwd_input = form.password.data or ""
        success, user = auth_service.login(user_input, pwd_input)
        if not success:
            if user:
                flash('Mot de passe incorrect.', 'danger')
            else:
                flash('Utilisateur non trouvé.', 'danger')
        else:
            flash('Connexion réussie.', 'success')
            return redirect(url_for('home'))

    # Afficher le formulaire de connexion
    return render_template('user/login.html', form=form)
