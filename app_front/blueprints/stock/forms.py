"""Module contenant les formulaires liés à la gestion des stocks."""

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange, Optional

class OrderInCreateForm(FlaskForm):
    """Formulaire de création de commande fournisseur (étape 1)."""

    supplier_id = StringField("Fournisseur", validators=[DataRequired()])
    submit = SubmitField("Créer la commande")
