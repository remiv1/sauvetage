"""Module contenant les formulaires liés à la gestion des stocks."""

from typing import Any
from collections import namedtuple
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


OrderTuple = namedtuple("Order", ["id", "general_object_id", "qty", "pu", "vat_rate"])

class OrderInCreateForm(FlaskForm):
    """Formulaire de création de commande fournisseur (étape 1)."""

    supplier_id = StringField("Fournisseur", validators=[DataRequired()])
    supplier_name = StringField(
        "Nom du fournisseur (auto-complete)", validators=[DataRequired()]
    )
    submit = SubmitField("Créer la commande")



class OrderInLineForm(FlaskForm):
    """Formulaire de ligne de commande fournisseur (étape 2)."""

    order_id = HiddenField("ID de la commande", validators=[DataRequired()])
    general_object_id = HiddenField("ID objet", validators=[DataRequired()])
    quantity = StringField("Quantité", validators=[DataRequired()])
    unit_price = StringField("Prix unitaire", validators=[DataRequired()])
    vat_rate = StringField("Taux de TVA", validators=[DataRequired()])
    submit = SubmitField("Ajouter à la commande")

    def validate_form_data(self, reservation: bool = False) -> OrderTuple:
        """
        Valide si les données sont complètes pour être utilisées.

        Return:
            OrderTuple: Un namedtuple contenant les données validées
            (order_id, general_object_id, quantity, unit_price, vat_rate).
        Raises:
            TypeError: Si les données du formulaire sont invalides.
            ValueError: Si les données du formulaire sont incomplètes.
        """
        try:
            order_id = int(self.order_id.data or 0)
            general_object_id = int(self.general_object_id.data or 0)
            quantity = int(self.quantity.data or 0)
            if not reservation:
                unit_price = float(self.unit_price.data or 0)
                vat_rate = float(self.vat_rate.data or 0)
                ok = (
                    order_id != 0
                    and general_object_id != 0
                    and quantity > 0
                    and unit_price != 0
                    and vat_rate != 0
                )
            else:
                unit_price = None
                vat_rate = None
                ok = order_id != 0 and general_object_id != 0 and quantity > 0
            if not ok:
                raise ValueError("Remplir tous les champs du formulaire.")
            return OrderTuple(order_id, general_object_id, quantity, unit_price, vat_rate)
        except (ValueError, TypeError) as e:
            raise TypeError("Données du formulaire invalides : " + str(e)) from e

    def line_to_form(self, line: Any):
        """Remplit les champs du formulaire à partir d'une ligne de commande existante."""
        self.order_id.data = str(line.order_in_id)
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

    items = FieldList(FormField(KeyValueForm), min_entries=0)  # type: ignore[arg-type]


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
            ("lnk", "Lien"),
            ("img", "Image"),
            ("oth", "Autre"),
        ],
        validators=[DataRequired()],
    )
    alt_text = StringField("Texte alternatif pour les images")
    file_data = FileField("Fichier média")
    file_link = StringField("URL du fichier média (si type lien)")


class CreateObjectForm(FlaskForm):
    """Formulaire de création d'objet (étape 1)."""

    supplier_id = StringField("Fournisseur", validators=[DataRequired()])
    general_object_id = HiddenField("ID de l'objet (pour les mises à jour)")
    supplier_name = StringField(
        "Nom du fournisseur (auto-complete)", validators=[DataRequired()]
    )
    general_object_type = SelectField(
        "Type d'objet",
        choices=[
            ("book", "Livre"),
            ("dvd", "DVD"),
            ("cd", "CD"),
            ("games", "Jeux"),
            ("spiritual_object", "Objet spirituel"),
            ("other", "Autre"),
        ],
        validators=[DataRequired()],
    )
    ean_13 = StringField("EAN13", validators=[DataRequired()])
    name = StringField("Nom de l'objet", validators=[DataRequired()])
    description = TextAreaField("Description de l'objet", render_kw={"rows": 4})
    price = StringField("Prix de vente", validators=[DataRequired()])
    purchase_price = StringField("Prix d'achat")
    vat_rate_id = SelectField(
        "Taux de TVA",
        coerce=str,
        choices=[("", "— Aucun —")],
        validate_choice=False,
    )
    book = FormField(BookForm)  # type: ignore[arg-type]
    object_tags = FieldList(FormField(TagForm), min_entries=0)  # type: ignore[arg-type]
    obj_metadatas = FormField(MetadataForm)  # type: ignore[arg-type]
    media_files = FieldList(FormField(MediaFileForm), min_entries=0)  # type: ignore[arg-type]
    submit = SubmitField("Valider")

    def populate_from_object(self, obj: Any):
        """Remplit les champs du formulaire à partir d'un objet existant."""
        self.general_object_id.data = str(obj.id)
        self.supplier_id.data = str(obj.supplier_id)
        self.supplier_name.data = obj.supplier.name
        self.general_object_type.data = obj.general_object_type
        self.ean_13.data = obj.ean13
        self.name.data = obj.name
        self.description.data = obj.description
        self.price.data = str(obj.price)
        self.purchase_price.data = str(obj.purchase_price) if obj.purchase_price is not None else ""
        self.vat_rate_id.data = str(obj.vat_rate_id) if obj.vat_rate_id is not None else ""

        self._populate_book(obj.book)
        self._populate_object_tags(obj.object_tags)
        self._populate_obj_metadatas(obj.obj_metadatas)
        self._populate_media_files(obj.media_files)

    def _populate_book(self, book: Any):
        if not book:
            return
        self.book.author.data = book.author or ""
        self.book.diffuser.data = book.diffuser or ""
        self.book.editor.data = book.editor or ""
        self.book.genre.data = book.genre or ""
        self.book.publication_year.data = str(book.publication_year) \
                                                if book.publication_year is not None \
                                                else ""
        self.book.pages.data = str(book.pages) if book.pages is not None else ""

    def _populate_object_tags(self, object_tags: Any):
        while len(self.object_tags) > 0:
            self.object_tags.pop_entry()
        for ot in object_tags:
            # append_entry() retourne un FormField (Field) dont .id est la chaîne
            # HTML-id (Field.__init__ : self.id = id). Il faut passer par .form
            # pour accéder à la forme interne TagForm et utiliser l'accès par
            # subscript afin d'éviter tout conflit avec l'attribut d'instance.
            inner = self.object_tags.append_entry().form  # type: ignore[attr-defined]
            inner["id"].data = str(ot.id)
            inner["tag_id"].data = str(ot.tag_id)

    def _populate_obj_metadatas(self, obj_metadatas: Any):
        if not obj_metadatas:
            return
        data = obj_metadatas.semistructured_data
        if not isinstance(data, dict):
            return
        metadata_items: FieldList = self.obj_metadatas.form["items"]  # type: ignore[attr-defined]
        while len(metadata_items) > 0:
            metadata_items.pop_entry()
        for k, v in data.items():
            inner = metadata_items.append_entry().form  # type: ignore[attr-defined]
            inner["key"].data = k
            inner["value"].data = v

    def _populate_media_files(self, media_files: Any):
        while len(self.media_files) > 0:
            self.media_files.pop_entry()
        for mf in media_files:
            inner = self.media_files.append_entry().form  # type: ignore[attr-defined]
            inner["file_name"].data = mf.file_name or ""
            inner["file_type"].data = mf.file_type or ""
            inner["alt_text"].data = mf.alt_text or ""
            inner["file_link"].data = mf.file_link or ""


class ReceiveLineForm(FlaskForm):
    """Formulaire de réception d'une ligne de commande fournisseur."""

    line_id = HiddenField("ID de la ligne", validators=[DataRequired()])
    order_id = HiddenField("ID de la commande", validators=[DataRequired()])
    qty_received = StringField("Quantité reçue", validators=[DataRequired()])
    qty_cancelled = StringField("Quantité annulée", validators=[DataRequired()])
    submit = SubmitField("Valider la réception")

    def validate_receive_data(self, qty_ordered: int) -> tuple[int, int]:
        """Valide les données de réception.

        Args:
            qty_ordered: La quantité commandée de la ligne.

        Returns:
            tuple[int, int]: (qty_received, qty_cancelled)

        Raises:
            ValueError: Si les données sont invalides.
        """
        try:
            qty_r = int(self.qty_received.data or 0)
            qty_c = int(self.qty_cancelled.data or 0)
        except (ValueError, TypeError) as e:
            raise ValueError("Les quantités doivent être des nombres entiers.") from e

        if qty_r < 0 or qty_c < 0:
            raise ValueError("Les quantités ne peuvent pas être négatives.")
        if qty_r + qty_c > qty_ordered:
            raise ValueError(
                f"La somme reçus ({qty_r}) + annulés ({qty_c}) "
                f"dépasse la quantité commandée ({qty_ordered})."
            )
        if qty_r == 0 and qty_c == 0:
            raise ValueError("Veuillez saisir au moins une quantité reçue ou annulée.")
        return qty_r, qty_c


class ExternalRefForm(FlaskForm):
    """Formulaire de mise à jour de la référence externe d'une commande."""

    external_ref = StringField("Référence fournisseur")
    submit = SubmitField("Mettre à jour")
