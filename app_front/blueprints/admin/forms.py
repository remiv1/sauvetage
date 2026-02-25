"""
Module contenant les formulaires liés à l'administration :
- First-user : Formulaire de création du premier utilisateur admin.
"""

from flask_wtf import FlaskForm
from wtforms import (
    StringField, PasswordField, SubmitField, EmailField
)
from wtforms.validators import DataRequired

class FirstUserForm(FlaskForm):
    """Formulaire de création du premier utilisateur admin."""
    username = StringField('Identifiant', validators=[DataRequired()])
    email = EmailField('Email', validators=[DataRequired()])
    password = PasswordField('Mot de passe', validators=[DataRequired()])
    confirm_password = PasswordField('Confirmer le mot de passe', validators=[DataRequired()])
    submit = SubmitField('Créer un compte')
    permissions = StringField('Permissions', default='9', validators=[DataRequired()])
