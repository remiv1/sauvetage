"""Module contenant les formulaires liés à la gestion des fournisseurs."""

from flask_wtf import FlaskForm
from wtforms import BooleanField, SelectMultipleField, StringField, SubmitField
from wtforms.fields import TimeField
from wtforms.validators import DataRequired, Optional
from wtforms.widgets import CheckboxInput, ListWidget

COLLECT_DAY_CHOICES = [
    ("1", "Lundi"),
    ("2", "Mardi"),
    ("3", "Mercredi"),
    ("4", "Jeudi"),
    ("5", "Vendredi"),
    ("6", "Samedi"),
    ("7", "Dimanche"),
]


class SupplierCreateForm(FlaskForm):
    """Formulaire de création de fournisseur."""

    supplier_name = StringField("Nom du fournisseur", validators=[DataRequired()])
    gln13 = StringField("Code GLN", validators=[DataRequired()])
    siren_siret = StringField("SIREN / SIRET")
    vat_number = StringField("Numéro de TVA")
    address = StringField("Adresse")
    contact_email = StringField("Email de contact")
    contact_phone = StringField("Téléphone de contact")
    contact_fax = StringField("Fax de contact")
    web_site = StringField("Site web")
    collect_days = SelectMultipleField(
        "Jours de collecte",
        choices=COLLECT_DAY_CHOICES,
        validators=[Optional()],
        option_widget=CheckboxInput(),
        widget=ListWidget(prefix_label=False),
    )
    cutoff_time = TimeField(
        "Heure limite",
        validators=[Optional()],
        format="%H:%M",
    )
    is_active = BooleanField("Actif")
    edi_active = BooleanField("Actif EDI")
    submit = SubmitField("Créer le fournisseur")


class SupplierEditForm(FlaskForm):
    """Formulaire d'édition d'un fournisseur existant."""

    supplier_name = StringField("Nom du fournisseur", validators=[DataRequired()])
    gln13 = StringField("Code GLN", validators=[DataRequired()])
    siren_siret = StringField("SIREN / SIRET")
    vat_number = StringField("Numéro de TVA")
    address = StringField("Adresse")
    contact_email = StringField("Email de contact")
    contact_phone = StringField("Téléphone de contact")
    contact_fax = StringField("Fax de contact")
    web_site = StringField("Site web")
    collect_days = SelectMultipleField(
        "Jours de collecte",
        choices=COLLECT_DAY_CHOICES,
        validators=[Optional()],
        option_widget=CheckboxInput(),
        widget=ListWidget(prefix_label=False),
    )
    cutoff_time = TimeField(
        "Heure limite",
        validators=[Optional()],
        format="%H:%M",
    )
    is_active = BooleanField("Actif")
    edi_active = BooleanField("Actif EDI")
    submit = SubmitField("Enregistrer")
