"""
Module contenant les formulaires liés à l'administration :
- First-user : Formulaire de création du premier utilisateur admin.
- VatRateForm : Formulaire de création/modification d'un taux de TVA.
- UserCreateAdminForm : Formulaire de création d'un utilisateur (depuis l'admin).
- UserEditPermissionsForm : Formulaire de modification des permissions.
"""

from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    PasswordField,
    SubmitField,
    EmailField,
    DecimalField,
    IntegerField,
    DateTimeLocalField,
    SelectMultipleField,
    widgets,
)
from wtforms.validators import DataRequired, NumberRange, Optional


class FirstUserForm(FlaskForm):
    """Formulaire de création du premier utilisateur admin."""

    username = StringField("Identifiant", validators=[DataRequired()])
    email = EmailField("Email", validators=[DataRequired()])
    password = PasswordField("Mot de passe", validators=[DataRequired()])
    confirm_password = PasswordField(
        "Confirmer le mot de passe", validators=[DataRequired()]
    )
    submit = SubmitField("Créer un compte")
    permissions = StringField("Permissions", default="9", validators=[DataRequired()])


# Codes TVA disponibles
VAT_CODE_CHOICES = [
    ("0", "0 — Super-réduit (2,1 %)"),
    ("1", "1 — Réduit (5,5 %)"),
    ("2", "2 — Intermédiaire (10 %)"),
    ("3", "3 — Normal (20 %)"),
]

# Noms lisibles des permissions
PERMISSION_CHOICES = [
    ("1", "Admin"),
    ("2", "Comptable"),
    ("3", "Commercial"),
    ("4", "Logistique"),
    ("5", "Support"),
    ("6", "Informatique"),
    ("7", "RH"),
    ("8", "Direction"),
    ("9", "Super Admin"),
]


class MultiCheckboxField(SelectMultipleField):
    """Champ multi-sélection avec des cases à cocher."""
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()


class VatRateForm(FlaskForm):
    """Formulaire de création/modification d'un taux de TVA."""

    code = IntegerField(
        "Code TVA",
        validators=[DataRequired(), NumberRange(min=0, max=40)],
    )
    rate = DecimalField(
        "Taux (%)",
        places=2,
        validators=[DataRequired(), NumberRange(min=0, max=100)],
    )
    label = StringField("Libellé", validators=[DataRequired()])
    date_start = DateTimeLocalField(
        "Date de début", format="%Y-%m-%dT%H:%M", validators=[DataRequired()]
    )
    date_end = DateTimeLocalField(
        "Date de fin", format="%Y-%m-%dT%H:%M", validators=[Optional()]
    )
    submit = SubmitField("Enregistrer")


class UserCreateAdminForm(FlaskForm):
    """Formulaire de création d'un utilisateur depuis l'admin."""

    username = StringField("Identifiant", validators=[DataRequired()])
    email = EmailField("Email", validators=[DataRequired()])
    password = PasswordField("Mot de passe", validators=[DataRequired()])
    permissions = MultiCheckboxField("Permissions", choices=PERMISSION_CHOICES)
    submit = SubmitField("Créer l'utilisateur")


class UserEditPermissionsForm(FlaskForm):
    """Formulaire de modification des permissions d'un utilisateur."""

    email = EmailField("Email", validators=[DataRequired()])
    permissions = MultiCheckboxField("Permissions", choices=PERMISSION_CHOICES)
    submit = SubmitField("Enregistrer")
