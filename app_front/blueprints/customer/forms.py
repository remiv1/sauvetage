"""
Module comprenant les formulaires liés aux clients :
- CustomerMainForm : Formulaire de création de client.
- AddressForm : Formulaire de création d'adresse pour un client.
- EmailForm : Formulaire de création d'email pour un client.
- PhoneForm : Formulaire de création de téléphone pour un client.
"""

from flask_wtf import FlaskForm
from wtforms import (
    StringField, SubmitField, EmailField, SelectField
)
from wtforms.validators import DataRequired

class ActivateCustomerForm(FlaskForm):
    """Formulaire pour activer un client."""
    submit = SubmitField('Activer le client')

class DeactivateCustomerForm(FlaskForm):
    """Formulaire pour désactiver un client."""
    submit = SubmitField('Désactiver le client')

class CustomerMainForm(FlaskForm):
    """Formulaire de création de client."""
    customer_type = SelectField("Part/Pro",
                                choices=[
                                    ('part', 'Particulier'),
                                    ('pro', 'Professionnel')
                                ],
                                validators=[DataRequired()])

    # Client Particulier
    civil_title = SelectField("Civilité",
                              choices=[
                                  ('m', 'M.'), ('mme', 'Mme'),
                                  ('mlle', 'Mlle'), ('ab', 'Abbé'),
                                  ('sr', 'Sr'), ('dr', 'Dr'),
                              ],
                              validators=[DataRequired()])
    first_name = StringField('Prénom', validators=[DataRequired()])
    last_name = StringField('Nom', validators=[DataRequired()])
    date_of_birth = StringField('Date de naissance (YYYY-MM-DD)', validators=[DataRequired()])

    # Client Professionnel
    company_name = StringField('Raison sociale', validators=[DataRequired()])
    siret_number = StringField('Numéro SIRET', validators=[DataRequired()])
    vat_number = StringField('Numéro de TVA', validators=[DataRequired()])
    submit = SubmitField('Créer un client')

class AddressForm(FlaskForm):
    """Formulaire de création d'adresse pour un client."""
    address_name = StringField('Nom de l\'adresse (ex: Domicile, Travail)',
                               validators=[DataRequired()])
    address_line_1 = StringField('Adresse', validators=[DataRequired()])
    address_line_2 = StringField('Complément d\'adresse')
    city = StringField('Ville', validators=[DataRequired()])
    state = StringField('État/Région', validators=[DataRequired()])
    postal_code = StringField('Code postal', validators=[DataRequired()])
    country = StringField('Pays', validators=[DataRequired()])
    submit = SubmitField('Ajouter une adresse')

class EmailForm(FlaskForm):
    """Formulaire de création d'email pour un client."""
    email_name = StringField('Nom de l\'email (ex: Personnel, Professionnel)',
                             validators=[DataRequired()])
    email = EmailField('Email', validators=[DataRequired()])
    submit = SubmitField('Ajouter un email')

class PhoneForm(FlaskForm):
    """Formulaire de création de téléphone pour un client."""
    phone_name = StringField('Nom du téléphone (ex: Personnel, Professionnel)',
                             validators=[DataRequired()])
    phone_number = StringField('Numéro de téléphone', validators=[DataRequired()])
    submit = SubmitField('Ajouter un numéro de téléphone')
