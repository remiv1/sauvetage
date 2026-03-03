"""Module contenant les formulaires liés à la gestion des stocks."""

from flask_wtf import FlaskForm
from wtforms import (StringField, TextAreaField, DecimalField, SelectField, SubmitField,
    HiddenField, FileField, BooleanField)
from wtforms.validators import DataRequired, Length, NumberRange, Optional, Email

class OrderInCreateForm(FlaskForm):
    """Formulaire de création de commande fournisseur (étape 1)."""

    order_ref = StringField("Numéro de commande",
        validators=[DataRequired(), Length(max=255)])
    external_ref = StringField("Référence externe",
        validators=[DataRequired(), Length(max=255)])
    supplier_id = HiddenField("Fournisseur (ID)",
        validators=[DataRequired()])
    supplier_name = StringField("Fournisseur",
        validators=[DataRequired(), Length(max=255)],
        render_kw={"autocomplete": "off"})
    value = DecimalField("Valeur totale",
        validators=[Optional(), NumberRange(min=0)],
        render_kw={"step": "0.01"})
    submit = SubmitField("Créer la commande")