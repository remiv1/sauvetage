"""Module contenant les formulaires liés à la gestion des fournisseurs."""

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired


class SupplierCreateForm(FlaskForm):
    """Formulaire de création de fournisseur."""

    supplier_name = StringField("Nom du fournisseur", validators=[DataRequired()])
    gln13 = StringField("Code GLN", validators=[DataRequired()])
    contact_email = StringField("Email de contact")
    contact_phone = StringField("Téléphone de contact")
    submit = SubmitField("Créer le fournisseur")


class SupplierEditForm(FlaskForm):
    """Formulaire d'édition d'un fournisseur existant."""

    supplier_name = StringField("Nom du fournisseur", validators=[DataRequired()])
    gln13 = StringField("Code GLN", validators=[DataRequired()])
    contact_email = StringField("Email de contact")
    contact_phone = StringField("Téléphone de contact")
    submit = SubmitField("Enregistrer")
