"""Module contenant les formulaires liés à la gestion des stocks."""

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired

class OrderInCreateForm(FlaskForm):
    """Formulaire de création de commande fournisseur (étape 1)."""

    supplier_id = StringField("Fournisseur", validators=[DataRequired()])
    submit = SubmitField("Créer la commande")

class OrderInLineForm(FlaskForm):
    """Formulaire de ligne de commande fournisseur (étape 2)."""
    general_object_id = StringField("Article", validators=[DataRequired()])
    quantity = StringField("Quantité", validators=[DataRequired()])
    unit_price = StringField("Prix unitaire", validators=[DataRequired()])
    vat_rate = StringField("Taux de TVA", validators=[DataRequired()])
    submit = SubmitField("Ajouter à la commande")
