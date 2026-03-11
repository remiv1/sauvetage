"""Module contenant les formulaires liés à la gestion des stocks."""

from typing import Any
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired
from wtforms import HiddenField


class OrderInCreateForm(FlaskForm):
    """Formulaire de création de commande fournisseur (étape 1)."""

    supplier_id = StringField("Fournisseur", validators=[DataRequired()])
    supplier_name = StringField("Nom du fournisseur (auto-complete)",
                                validators=[DataRequired()])
    submit = SubmitField("Créer la commande")


class OrderInLineForm(FlaskForm):
    """Formulaire de ligne de commande fournisseur (étape 2)."""

    order_id = HiddenField("ID de la commande", validators=[DataRequired()])
    general_object_id = HiddenField("ID objet", validators=[DataRequired()])
    quantity = StringField("Quantité", validators=[DataRequired()])
    unit_price = StringField("Prix unitaire", validators=[DataRequired()])
    vat_rate = StringField("Taux de TVA", validators=[DataRequired()])
    submit = SubmitField("Ajouter à la commande")

    def validate_form_data(self) -> tuple[int, int, int, float, float]:
        """
        Valide si les données sont complètes pour être utilisées.
        
        Return:
            tuple[int, int, int, float, float]: Un tuple contenant les données validées
            (order_id, general_object_id, quantity, unit_price, vat_rate).
        Raises:
            TypeError: Si les données du formulaire sont invalides.
            ValueError: Si les données du formulaire sont incomplètes.
        """
        try:
            order_id = int(self.order_id.data or 0)
            general_object_id = int(self.general_object_id.data or 0)
            quantity = int(self.quantity.data or 0)
            unit_price = float(self.unit_price.data or 0)
            vat_rate = float(self.vat_rate.data or 0)
            if (
                order_id == 0
                or general_object_id == 0
                or quantity == 0
                or unit_price == 0
                or vat_rate == 0
            ):
                raise ValueError("Remplir tous les champs du formulaire.")
            return (order_id, general_object_id, quantity, unit_price, vat_rate)
        except (ValueError, TypeError) as e:
            raise TypeError("Données du formulaire invalides : " + str(e)) from e


    def line_to_form(self, line: Any):
        """Remplit les champs du formulaire à partir d'une ligne de commande existante."""
        self.order_id.data = str(line.order_id)
        self.general_object_id.data = str(line.general_object_id)
        self.quantity.data = str(line.qty_ordered)
        self.unit_price.data = str(line.unit_price)
        self.vat_rate.data = str(line.vat_rate)
