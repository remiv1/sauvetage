"""Module contenant les formulaires liés à la gestion des commandes."""

from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, DecimalField, SelectField, SubmitField, HiddenField
from wtforms.validators import DataRequired, NumberRange


class OrderCreateForm(FlaskForm):
    """Formulaire de création d'une commande (sélection du client)."""

    customer_id = HiddenField("Client", validators=[DataRequired()])
    submit = SubmitField("Créer la commande")


class OrderLineForm(FlaskForm):
    """Formulaire d'ajout d'une ligne de commande."""

    general_object_id = HiddenField("Article", validators=[DataRequired()])
    quantity = IntegerField(
        "Quantité", validators=[DataRequired(), NumberRange(min=1)]
    )
    unit_price = DecimalField(
        "Prix unitaire HT (€)", validators=[DataRequired(), NumberRange(min=0)], places=2
    )
    vat_rate = DecimalField(
        "TVA (%)", validators=[DataRequired(), NumberRange(min=0, max=100)], places=1
    )
    discount = DecimalField(
        "Remise (%)", validators=[NumberRange(min=0, max=100)], places=2, default=0
    )
    submit = SubmitField("Ajouter la ligne")


class QuickCustomerForm(FlaskForm):
    """Formulaire de création rapide d'un client depuis la commande."""

    customer_type = SelectField(
        "Type",
        choices=[("part", "Particulier"), ("pro", "Professionnel")],
        validators=[DataRequired()],
    )
    # Particulier
    civil_title = SelectField(
        "Civilité",
        choices=[
            ("", "-- Civilité --"),
            ("m", "M."),
            ("mme", "Mme"),
            ("mlle", "Mlle"),
        ],
    )
    first_name = StringField("Prénom")
    last_name = StringField("Nom")
    # Professionnel
    company_name = StringField("Raison sociale")
    submit = SubmitField("Créer le client")
