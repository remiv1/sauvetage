"""
Module contenant les formulaires liés à l'inventaire :
- EanInputForm : Formulaire de saisie des EAN13.
- ProductCreateForm : Formulaire de création de produit (modale).
- SupplierCreateForm : Formulaire de création de fournisseur (imbriqué).
"""

from flask_wtf import FlaskForm
from wtforms import (StringField, TextAreaField, DecimalField, SelectField, SubmitField,
    HiddenField, FileField, BooleanField)
from wtforms.validators import DataRequired, Length, NumberRange, Optional, Email

GENERAL_OBJECT_STRING = "Identifiant de l'objet général (ID)"

class EanInputForm(FlaskForm):
    """Formulaire de saisie des EAN13 (étape 2)."""

    inventory_type = SelectField("Type d'inventaire",
        choices=[("complete", "Inventaire Complet"),
                 ("partial", "Inventaire Partiel"),
                 ("single", "Article Unique")],
        validators=[DataRequired()])
    category = SelectField("Catégorie / Rayon",
        choices=[("livres", "Livres"),
                 ("jeux", "Jeux"),
                 ("musique", "Musique"),
                 ("objets", "Objets")],
        validators=[Optional(), Length(max=120)])
    ean_textarea = TextAreaField("Liste d'EAN13",
        validators=[Optional()])
    ean_single = StringField("Code EAN13",
        validators=[Optional(), Length(min=13, max=13)])
    submit = SubmitField("Analyser")

class ProductCreateForm(FlaskForm):
    """Formulaire de création de produit (modale — étape 4).
    Le champ general_object_type permet de choisir entre un livre et un autre
    type d'objet (jeu, objet de piété, etc.). Les champs auteur et
    éditeur ne sont pertinents que pour les livres.
    """
    ean13 = StringField("EAN13",
        validators=[DataRequired(), Length(min=13, max=13)],
        render_kw={"readonly": True})
    general_object_type = SelectField("Type de produit",
        choices=[("book", "Livre"),
                 ("other", "Autre (jeu, objet de piété…)")],
        default="book",
        validators=[DataRequired()])
    add_to_dilicom = BooleanField("Ajouter à la base Dilicom",
        default=False)
    supplier_id = HiddenField("Fournisseur (ID)",
        validators=[DataRequired()])
    supplier_name = StringField("Fournisseur",
        validators=[DataRequired(), Length(max=255)],
        render_kw={"autocomplete": "off"})
    name = StringField("Titre / Nom",
        validators=[DataRequired(), Length(max=255)])
    description = TextAreaField("Description",
        validators=[Optional()])
    price = DecimalField("Prix",
        places=2,
        validators=[DataRequired(), NumberRange(min=0)])
    is_active = SelectField("Actif",
        choices=[("yes", "Oui"), ("no", "Non")],
        validators=[Optional(), Length(max=10)])
    author = StringField("Auteur",
        validators=[Optional(), Length(max=255)])
    diffuser = StringField("Distributeur",
        validators=[Optional(), Length(max=255)])
    editor = StringField("Éditeur",
        validators=[Optional(), Length(max=255)])
    genre = StringField("Catégorie/Genre",
        validators=[Optional(), Length(max=120)])
    publication_year = StringField("Année de publication",
        validators=[Optional(), Length(max=4)])
    pages = StringField("Nombre de pages",
        validators=[Optional(), Length(max=10)])
    submit = SubmitField("Créer")

class TagCreateForm(FlaskForm):
    """Formulaire de création de tags."""
    name = StringField("Nom du tag",
        validators=[DataRequired(), Length(max=50)])
    description = TextAreaField("Description du tag",
        validators=[Optional(), Length(max=255)])
    submit = SubmitField("Ajouter le tag")

class JoinTagObjectForm(FlaskForm):
    """Formulaire d'association d'un tag à un objet."""
    general_object_id = HiddenField(GENERAL_OBJECT_STRING,
        validators=[DataRequired()])
    tag_name = StringField("Nom du tag",
        validators=[DataRequired(), Length(max=50)],
        render_kw={"autocomplete": "on"})
    tag_id = SelectField("Tag", # Rempli dynamiquement en JS
        validators=[DataRequired()])
    submit = SubmitField("Associer le tag")

class MetadataForm(FlaskForm):
    """Formulaire de saisie de métadonnées supplémentaires (étape 5)."""
    general_object_id = HiddenField(GENERAL_OBJECT_STRING,
        validators=[DataRequired()])
    key = StringField("Clé",
        validators=[DataRequired(), Length(max=50)])
    value = StringField("Valeur",
        validators=[DataRequired(), Length(max=255)])
    submit = SubmitField("Ajouter la métadonnée")

class MediaFilesForm(FlaskForm):
    """Formulaire de gestion des fichiers médias (étape 6)."""
    general_object_id = HiddenField(GENERAL_OBJECT_STRING,
        validators=[DataRequired()])
    file_name = StringField("Fichier",
        validators=[DataRequired(), Length(max=255)])
    file_type = SelectField("Type de fichier",
        choices=[("lien/link", "Lien"),
                 ("image/jpg", "JPG"),
                 ("image/svg", "SVG"),
                 ("image/png", "PNG"),
                 ("image/gif", "GIF"),
                 ("image/webp", "WebP")],
        validators=[DataRequired()])
    alt_text = StringField("Texte alternatif",
        validators=[Optional(), Length(max=255)])
    file_data = FileField("Fichier",
        validators=[DataRequired()])
    file_link = StringField("URL du fichier",
        validators=[Optional(), Length(max=255)])
    description = StringField("Description du fichier",
        validators=[Optional(), Length(max=255)])
    submit = SubmitField("Ajouter le fichier")

class SupplierCreateForm(FlaskForm):
    """Formulaire de création de fournisseur (imbriqué dans la modale produit)."""
    name = StringField("Nom du fournisseur",
        validators=[Optional(), Length(min=1, max=255)])  # Optional pour éviter required="" en HTML
    gln13 = StringField("GLN13 (optionnel)",
        validators=[Optional(), Length(max=13)])
    contact_email = StringField("Email",
        validators=[Optional(), Email()])
    contact_phone = StringField("Téléphone",
        validators=[Optional(), Length(max=20)])
    submit = SubmitField("Créer le fournisseur")
