"""Blueprint API HTMX pour le module stock."""

from flask import Blueprint, render_template, request, flash
from app_front.blueprints.stock.forms import (
    CreateObjectForm,
    OrderInCreateForm,
    OrderInLineForm,
)
from app_front.blueprints.stock.utils import (
    get_supplier_orders,
    get_supplier_returns,
    get_order_by_id,
    get_return_by_id,
    cancel_supplier_order,
    create_order_in_db,
    create_order_in_line_db,
    search_stock_global,
    get_dilicom_referencial,
    get_object_by_id,
    create_object_complete,
    search_book_field,
    search_tags,
    create_tag,
)

bp_stock_htmx = Blueprint(
    "stock_htmx",
    __name__,
    url_prefix="/stock/htmx",
    template_folder="htmx_templates/stock",
)

EDIT_TABLE = "htmx_templates/stock/orders/sections/view.html"
NEW_LINE = "htmx_templates/stock/orders/fragments/new_line.html"
SECTION_NEW = "htmx_templates/stock/orders/sections/new.html"
SECTION_HOME = "htmx_templates/stock/orders/sections/home.html"
SECTION_CANCELED = "htmx_templates/stock/orders/sections/canceled.html"


@bp_stock_htmx.get("/cleared")
def cleared():
    """ Retourne une section vide pour réinitialiser l'affichage (HTMX). """
    return ""


@bp_stock_htmx.get("/orders")
def orders():
    """Retourne la section complète de gestion des commandes fournisseurs (HTMX)."""
    orders_list = get_supplier_orders()
    return render_template(SECTION_HOME, orders=orders_list)


@bp_stock_htmx.get("/returns")
def returns():
    """Retourne la section complète de gestion des retours fournisseurs (HTMX)."""
    returns_list = get_supplier_returns()
    return render_template(SECTION_HOME, returns=returns_list)


@bp_stock_htmx.route("/orders/section/create", methods=["GET", "POST"])
def new_order_section():
    """Retourne la section complète pour la création d'une nouvelle commande fournisseur (HTMX)."""
    form = OrderInCreateForm()
    if form.validate_on_submit():
        id_order = create_order_in_db(form)
        if not id_order:
            raise ValueError("Failed to create order in database")
        order = get_order_by_id(id_order)
        return render_template(EDIT_TABLE, view_state='new', order=order)
    return render_template(SECTION_NEW, form=form)


@bp_stock_htmx.route("/orders/<int:order_id>/section/edit", methods=["GET", "POST"])
def edit_order(order_id: int):
    """Retourne la section complète d'une commande fournisseur existante (HTMX)."""
    if request.method == "POST":
        form = OrderInCreateForm()
        if form.validate_on_submit():
            pass  # TODO: implémenter la logique de mise à jour de la commande
    order = get_order_by_id(order_id)
    return render_template(
        EDIT_TABLE,
        id_order=order_id,
        order=order,
        view_state='edit'
        )


@bp_stock_htmx.route("/orders/<int:order_id>/line/create", methods=["GET", "POST"])
def new_order_line_form(order_id: int):
    """Retourne le formulaire de création d'une ligne de commande fournisseur (HTMX)."""
    form = OrderInLineForm()
    form.order_id.data = str(order_id)
    if form.validate_on_submit():
        id_line = create_order_in_line_db(form)
        if not id_line:
            raise ValueError("Failed to create order line in database")
        order = get_order_by_id(order_id)
        return render_template(
            EDIT_TABLE,
            order=order,
            form=form,
            view_state='new'
            )
    return render_template(NEW_LINE, form=form, action='create')


@bp_stock_htmx.route("/orders/<int:order_id>/line/<int:line_id>/<action>",
                     methods=["GET", "POST"])
def edit_order_line(order_id: int, line_id: int, action: str):
    """Retourne le formulaire d'édition d'une ligne de commande fournisseur (HTMX)."""
    # Récupération du formulaire
    form = OrderInLineForm()

    # Gestion de la méthode POST pour les actions d'édition ou de suppression
    if request.method == "POST":

        # Gestion de l'action d'édition
        if action == "edit":
            if form.validate_on_submit():
                create_order_in_line_db(form, action="edit", line_id=line_id)
                order = get_order_by_id(order_id)
                return render_template(
                    EDIT_TABLE,
                    order=order,
                    form=form,
                    view_state='edit'
                )
            flash("Données du formulaire invalides. Veuillez corriger les erreurs.", "error")
            return render_template(NEW_LINE, form=form)

        # Gestion de l'action de suppression
        if action == "delete":
            create_order_in_line_db(form, action="delete", line_id=line_id)
            order = get_order_by_id(order_id)
            return render_template(
                EDIT_TABLE,
                order=order,
                form=form,
                view_state='edit'
            )

    # Retour du formulaire de validation de la suppression
    if action == 'delete':
        return render_template(SECTION_CANCELED)

    # Sinon, si on est sur une action d'édition.
    order = get_order_by_id(order_id)
    line = next((l for l in order.orderin_lines if l.id == line_id), None)
    if not line:
        raise ValueError(f"Line with ID {line_id} not found in order {order_id}")

    # Remplissage du formulaire avec les données de la ligne existante
    form.line_to_form(line)

    return render_template(NEW_LINE, form=form)



@bp_stock_htmx.get("/orders/view/<int:order_id>")
def view_order(order_id: int):
    """Retourne la vue détaillée d'une commande fournisseur (HTMX)."""
    # Récupérer les détails de la commande à partir de l'ID
    order = get_order_by_id(order_id)
    return render_template(EDIT_TABLE, order=order, view_state='view')


@bp_stock_htmx.post("/orders/cancel/<int:order_id>")
def cancel_order(order_id: int):
    """Annule une commande fournisseur (HTMX)."""
    cancel_supplier_order(order_id)
    return render_template("htmx_templates/stock/orders/fragments/canceled.html")


@bp_stock_htmx.get("/returns/section/create")
def new_return_section():
    """Retourne la section complète pour la création d'un nouveau retour fournisseur (HTMX)."""
    form = OrderInCreateForm()
    template_path = "htmx_templates/stock/returns/sections/new.html"
    return render_template(template_path, form=form)


@bp_stock_htmx.get("/returns/view/<int:return_id>")
def view_return(return_id: int):
    """Retourne la vue détaillée d'un retour fournisseur (HTMX)."""
    # Récupérer les détails du retour à partir de l'ID
    return_info = get_return_by_id(return_id)
    return render_template("htmx_templates/stock/returns/sections/view.html",
                           return_info=return_info)


@bp_stock_htmx.post("/returns/table/create")
def new_return_table():
    """Retourne une ligne de tableau pour une nouvelle ligne de retour fournisseur (HTMX)."""
    return render_template("htmx_templates/stock/returns/fragments/new_table.html")


@bp_stock_htmx.route("/returns/line/create", methods=["GET", "POST"])
def new_return_line_form():
    """Retourne le formulaire de création d'une ligne de retour fournisseur (HTMX)."""
    return render_template("htmx_templates/stock/returns/fragments/new_line.html")


# ============================================================================
# Recherche globale de stock
# ============================================================================

SEARCH_TABLE = "htmx_templates/stock/search/table.html"
DILICOM_MODAL = "htmx_templates/stock/search/dilicom_modal.html"


@bp_stock_htmx.get("/search/table")
def search_table():
    """Retourne le tableau filtré du stock global (HTMX)."""
    name = request.args.get("name", "").strip() or None
    ean13 = request.args.get("ean13", "").strip() or None
    supplier_id_str = request.args.get("supplier_id", "").strip()
    supplier_id = int(supplier_id_str) if supplier_id_str else None
    object_type = request.args.get("object_type", "").strip() or None
    is_active_str = request.args.get("is_active", "").strip()
    is_active = None
    if is_active_str == "true":
        is_active = True
    elif is_active_str == "false":
        is_active = False
    dilicom_status = request.args.get("dilicom_status", "").strip() or None
    page_str = request.args.get("page", "1").strip()
    page = max(1, int(page_str)) if page_str.isdigit() else 1

    result = search_stock_global(
        name=name,
        ean13=ean13,
        supplier_id=supplier_id,
        object_type=object_type,
        is_active=is_active,
        dilicom_status=dilicom_status,
        page=page,
    )
    return render_template(SEARCH_TABLE, **result)


@bp_stock_htmx.get("/search/dilicom/<int:object_id>")
def dilicom_modal(object_id: int):
    """Retourne la modale Dilicom pour un objet donné (HTMX)."""
    dilicom_ref, obj = get_dilicom_referencial(object_id)
    if dilicom_ref is None and obj is None:
        return "<p>Aucun référentiel Dilicom trouvé pour cet objet.</p>"

    return render_template(
        DILICOM_MODAL,
        obj=obj,
        dilicom_ref=dilicom_ref,
    )


# ============================================================================
# Routes pour la gestion unitaire des objets (création / vue)
# ============================================================================

OBJECT_FORM = "htmx_templates/stock/search/single_object_form.html"
OBJECT_COMPLEMENT = "htmx_templates/stock/search/object_complement.html"
AUTOCOMPLETE_DROPDOWN = "htmx_templates/stock/search/autocomplete_dropdown.html"
TAG_AUTOCOMPLETE = "htmx_templates/stock/search/tag_autocomplete_dropdown.html"
TAG_SELECTED = "htmx_templates/stock/search/tag_selected.html"


@bp_stock_htmx.get("/search/object/autocomplete/<field>")
def object_autocomplete(field: str):
    """Retourne les suggestions d'autocomplete pour un champ donné (HTMX)."""
    q = request.args.get("q", "").strip()
    print(f"DEBUG Autocomplete request for field '{field}' with query: '{q}'")
    print(f"DEBUG request.args: {dict(request.args)}")
    if len(q) < 1:
        return ""
    if field == "tag":
        results = search_tags(q)
        return render_template(TAG_AUTOCOMPLETE, results=results, query=q)
    else:
        results = search_book_field(field, q)
        return render_template(AUTOCOMPLETE_DROPDOWN, results=results, field=field)


@bp_stock_htmx.post("/search/object/tag/create")
def create_tag_htmx():
    """Crée un tag via HTMX et retourne le fragment de sélection."""
    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()
    if not name:
        return "<div class='dropdown-item text-danger'>Le nom est requis.</div>", 422
    try:
        tag = create_tag(name, description)
    except ValueError as exc:
        return f"<div class='dropdown-item text-danger'>{exc}</div>", 422
    return render_template(
        TAG_SELECTED,
        tag_id=tag["id"],
        tag_name=tag["name"],
        tag_description=tag["description"],
    )


@bp_stock_htmx.get("/search/object/form")
def object_form():
    """Retourne le formulaire de base de l'objet en mode création (HTMX)."""
    form = CreateObjectForm()
    return render_template(OBJECT_FORM, form=form, form_state="create")


@bp_stock_htmx.get("/search/object/view/<int:object_id>")
def object_view(object_id: int):
    """Retourne le formulaire de l'objet en mode consultation (HTMX)."""
    obj = get_object_by_id(object_id)
    if obj is None:
        return "<p>Objet introuvable.</p>", 404
    form = CreateObjectForm()
    form.supplier_id.data = str(obj.supplier_id)
    form.supplier_name.data = obj.supplier.name if obj.supplier else ""
    form.general_object_type.data = obj.general_object_type
    form.ean_13.data = obj.ean13
    form.name.data = obj.name
    form.description.data = obj.description or ""
    form.price.data = str(obj.price)
    return render_template(
        OBJECT_FORM, form=form, form_state="view", obj=obj,
    )


@bp_stock_htmx.get("/search/object/complement")
def object_complement():
    """Retourne le complément d'onglets en fonction du type sélectionné (HTMX)."""
    object_type = request.args.get("general_object_type", "other")
    form_state = request.args.get("form_state", "create")
    form = CreateObjectForm()
    return render_template(
        OBJECT_COMPLEMENT,
        form=form,
        object_type=object_type,
        form_state=form_state,
    )


@bp_stock_htmx.get("/search/object/complement/<int:object_id>")
def object_complement_view(object_id: int):
    """Retourne le complément d'onglets pré-rempli en mode consultation (HTMX)."""
    obj = get_object_by_id(object_id)
    if obj is None:
        return "<p>Objet introuvable.</p>", 404
    form = CreateObjectForm()
    if obj.book:
        form.book.author.data = obj.book.author or ""
        form.book.diffuser.data = obj.book.diffuser or ""
        form.book.editor.data = obj.book.editor or ""
        form.book.genre.data = obj.book.genre or ""
        form.book.publication_year.data = str(obj.book.publication_year or "")
        form.book.pages.data = str(obj.book.pages or "")
        form.book.add_to_dilicom.data = "true" if obj.book.add_to_dilicom else "false"
    return render_template(
        OBJECT_COMPLEMENT,
        form=form,
        object_type=obj.general_object_type,
        form_state="view",
        obj=obj,
    )


@bp_stock_htmx.route("/search/object/create", methods=["POST"])
def create_object():
    """Valide et crée un nouvel objet à partir du formulaire global (HTMX)."""
    form = CreateObjectForm()
    if form.validate_on_submit():
        try:
            new_obj = create_object_complete(form)
            return render_template(
                OBJECT_FORM, form=CreateObjectForm(),
                form_state="created", created_id=new_obj.id,
            )
        except ValueError as exc:
            flash(str(exc), "danger")
            return render_template(
                OBJECT_FORM, form=form, form_state="create",
            ), 422
    print(f"DEBUG Form errors: {form.errors}")
    return render_template(
        OBJECT_FORM, form=form, form_state="create",
    ), 422
