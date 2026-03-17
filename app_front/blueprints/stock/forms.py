"""Module contenant les formulaires liés à la gestion des stocks."""

from typing import Any
from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    FieldList,
    FormField,
    SubmitField,
    HiddenField,
    SelectField,
    FileField,
    TextAreaField,
)
from wtforms.validators import DataRequired


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


class BookForm(FlaskForm):
    """Formulaire de création/édition d'un livre."""
    class Meta:
        """Désactive CSRF pour ce formulaire imbriqué."""
        csrf = False  # Désactive CSRF pour ce formulaire imbriqué

    author = StringField("Auteur du livre")
    diffuser = StringField("Diffuseur du livre")
    editor = StringField("Éditeur du livre")
    genre = StringField("Genre du livre")
    publication_year = StringField("Année de publication du livre")
    pages = StringField("Nombre de pages du livre")


class KeyValueForm(FlaskForm):
    """Formulaire générique pour les paires clé-valeur."""
    class Meta:
        """Désactive CSRF pour ce formulaire imbriqué."""
        csrf = False  # Désactive CSRF pour ce formulaire imbriqué

    key = StringField("Clé", validators=[DataRequired()])
    value = StringField("Valeur", validators=[DataRequired()])


class MetadataForm(FlaskForm):
    """Formulaire de création/édition de métadonnée."""
    class Meta:
        """Désactive CSRF pour ce formulaire imbriqué."""
        csrf = False  # Désactive CSRF pour ce formulaire imbriqué

    items = FieldList(FormField(KeyValueForm), min_entries=0)   # type: ignore[arg-type]


class TagForm(FlaskForm):
    """Formulaire de création/édition de tag."""
    class Meta:
        """Désactive CSRF pour ce formulaire imbriqué."""
        csrf = False  # Désactive CSRF pour ce formulaire imbriqué
    id = HiddenField("ID de la liaison object_tags")
    tag_id = HiddenField("ID du tag")


class MediaFileForm(FlaskForm):
    """Formulaire de création/édition de fichier média."""
    class Meta:
        """Désactive CSRF pour ce formulaire imbriqué."""
        csrf = False  # Désactive CSRF pour ce formulaire imbriqué

    file_name = StringField("Nom du fichier média", validators=[DataRequired()])
    file_type = SelectField(
        "Type de fichier média",
        choices=[
            ('lnk', 'Lien'),
            ('img', 'Image'),
            ('oth', 'Autre'),
        ],
        validators=[DataRequired()]
    )
    alt_text = StringField("Texte alternatif pour les images")
    file_data = FileField("Fichier média")
    file_link = StringField("URL du fichier média (si type lien)")


class CreateObjectForm(FlaskForm):
    """Formulaire de création d'objet (étape 1)."""

    supplier_id = StringField("Fournisseur", validators=[DataRequired()])
    general_object_id = HiddenField("ID de l'objet (pour les mises à jour)")
    supplier_name = StringField("Nom du fournisseur (auto-complete)",
                                validators=[DataRequired()])
    general_object_type = SelectField("Type d'objet",
                                      choices=[
                                          ('book', 'Livre'),
                                          ('dvd', 'DVD'),
                                          ('cd', 'CD'),
                                          ('games', 'Jeux'),
                                          ('spiritual_object', 'Objet spirituel'),
                                          ('other', 'Autre'),
                                          ],
                                      validators=[DataRequired()]
                                     )
    ean_13 = StringField("EAN13", validators=[DataRequired()])
    name = StringField("Nom de l'objet", validators=[DataRequired()])
    description = TextAreaField("Description de l'objet", render_kw={"rows": 4})
    price = StringField("Prix de l'objet", validators=[DataRequired()])
    book = FormField(BookForm)  # type: ignore[arg-type]
    object_tags = FieldList(FormField(TagForm), min_entries=0) # type: ignore[arg-type]
    obj_metadatas = FormField(MetadataForm)  # type: ignore[arg-type]
    media_files = FieldList(FormField(MediaFileForm), min_entries=0)    # type: ignore[arg-type]
    submit = SubmitField("Valider")
