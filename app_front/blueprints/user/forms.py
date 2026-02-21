"""
Module contenant les formulaires liés à l'utilisateur :
- LoginForm : Formulaire de connexion pour les utilisateurs.
- UserCreateForm : Formulaire de création de compte utilisateur.
- UserEditForm : Formulaire d'édition de compte utilisateur.
- UserPasswordChangeForm : Formulaire de changement de mot de passe pour les utilisateurs.
"""

from flask_wtf import FlaskForm
from wtforms import (
    StringField, PasswordField, SubmitField, EmailField, SelectMultipleField, widgets
)
from wtforms.validators import DataRequired

class LoginForm(FlaskForm):
    """Formulaire de connexion pour les utilisateurs."""
    username = StringField('Identifiant', validators=[DataRequired()])
    password = PasswordField('Mot de passe', validators=[DataRequired()])
    submit = SubmitField('Se connecter')

class UserCreateForm(FlaskForm):
    """Formulaire de création de compte utilisateur."""
    username = StringField('Identifiant', validators=[DataRequired()])
    mail = EmailField('Email', validators=[DataRequired()])
    password = PasswordField('Mot de passe', validators=[DataRequired()])
    confirm_password = PasswordField('Confirmer le mot de passe', validators=[DataRequired()])
    submit = SubmitField('Créer un compte')
    permissions = SelectMultipleField(
        'Autorisations',
        choices=[
            ('1', 'Administration'), ('2', 'Comptabilité'), ('3', 'Commercial'),
            ('4', 'Logistique'), ('5', 'Support'), ('6', 'Informatique'),
            ('7', 'RH'), ('8', 'Direction'), ('9', 'Super Admin')
        ],
        option_widget=widgets.CheckboxInput(),
        widget=widgets.ListWidget(prefix_label=False),
        default='user'
    )

class UserEditForm(FlaskForm):
    """Formulaire d'édition de compte utilisateur."""
    username = StringField('Identifiant', validators=[DataRequired()])
    mail = EmailField('Email', validators=[DataRequired()])
    permissions = SelectMultipleField(
        'Autorisations',
        choices=[
            ('1', 'Administration'), ('2', 'Comptabilité'), ('3', 'Commercial'),
            ('4', 'Logistique'), ('5', 'Support'), ('6', 'Informatique'),
            ('7', 'RH'), ('8', 'Direction'), ('9', 'Super Admin')
        ],
        option_widget=widgets.CheckboxInput(),
        widget=widgets.ListWidget(prefix_label=False)
    )
    submit = SubmitField('Mettre à jour')

class UserPasswordChangeForm(FlaskForm):
    """Formulaire de changement de mot de passe pour les utilisateurs."""
    old_password = PasswordField('Ancien mot de passe', validators=[DataRequired()])
    new_password = PasswordField('Nouveau mot de passe', validators=[DataRequired()])
    new_password_confirm = PasswordField('Confirmer le mot de passe', validators=[DataRequired()])
    submit = SubmitField('Changer le mot de passe')
