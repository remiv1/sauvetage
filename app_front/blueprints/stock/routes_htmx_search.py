"""Blueprint API HTMX pour le module stock."""

from flask import Blueprint, make_response, render_template, request, flash
from app_front.blueprints.stock.forms import (
    CreateObjectForm,
)
from app_front.blueprints.stock.utils import (
    search_stock_global,
    get_dilicom_referencial,
    get_object_by_id,
    save_object_complete,
    search_book_field,
    search_tags,
    create_tag,
    toggle_object_active,
    add_object_to_dilicom,
    remove_object_from_dilicom,
)

bp_stock_htmx_search = Blueprint(
    "stock_htmx_search",
    __name__,
    url_prefix="/stock/htmx/search",
    template_folder="htmx_templates/stock",
)

TOGGLE_ACTIVE_MODAL = "htmx_templates/stock/search/toggle_active_modal.html"
SEARCH_TABLE = "htmx_templates/stock/search/table.html"
DILICOM_MODAL = "htmx_templates/stock/search/dilicom_modal.html"
UNKNOWN_OBJECT = "<p>Objet introuvable.</p>"
OBJECT_FORM = "htmx_templates/stock/search/single_object_form.html"
OBJECT_COMPLEMENT = "htmx_templates/stock/search/object_complement.html"
AUTOCOMPLETE_DROPDOWN = "htmx_templates/stock/search/autocomplete_dropdown.html"
TAG_AUTOCOMPLETE = "htmx_templates/stock/search/tag_autocomplete_dropdown.html"
TAG_SELECTED = "htmx_templates/stock/search/tag_selected.html"


@bp_stock_htmx_search.get("/cleared")
def cleared():
    """Retourne une section vide pour réinitialiser l'affichage (HTMX)."""
    return ""


@bp_stock_htmx_search.get("/table")
def search_table():
    """Retourne le tableau filtré du stock global (HTMX)."""
    name = request.args.get("name", "").strip() or None
    ean13 = request.args.get("ean13", "").strip() or None
    supplier_id_str = request.args.get("supplier_id", "").strip()
    supplier_id = int(supplier_id_str) if supplier_id_str else None
    object_type = request.args.get("object_type", "").strip() or None
    is_active_str = request.args.get("is_active", "true").strip()
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


@bp_stock_htmx_search.get("/dilicom/<int:object_id>")
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


@bp_stock_htmx_search.get("/object/autocomplete/<field>")
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


@bp_stock_htmx_search.post("/object/tag/create")
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


@bp_stock_htmx_search.get("/object/form")
def object_form():
    """Retourne le formulaire de base de l'objet en mode création (HTMX)."""
    form = CreateObjectForm()
    return render_template(OBJECT_FORM, form=form, form_state="create")


@bp_stock_htmx_search.get("/object/<action>/<int:object_id>")
def object_view_or_edit(action: str, object_id: int):
    """Retourne le formulaire de l'objet en mode consultation ou édition (HTMX)."""
    obj = get_object_by_id(object_id)
    if obj is None:
        return UNKNOWN_OBJECT, 404
    form = CreateObjectForm()
    form.populate_from_object(obj)
    return render_template(
        OBJECT_FORM,
        form=form,
        form_state=action,
        obj=obj,
    )


@bp_stock_htmx_search.get("/object/complement")
def object_complement():
    """Retourne le complément d'onglets en fonction du type sélectionné (HTMX)."""
    object_type = request.args.get("general_object_type", "other")
    form_state = request.args.get("form_state", "create")
    form = CreateObjectForm()
    obj = None
    if form_state == "edit" or form_state == "view":
        object_id = request.args.get("object_id")
        try:
            if object_id is None:
                raise ValueError("object_id est requis pour l'édition ou la consultation")
            object_id = int(object_id)
        except ValueError as exc:
            raise ValueError("object_id doit être un entier valide") from exc
        obj = get_object_by_id(object_id)
        if obj is None:
            raise ValueError("Objet introuvable pour l'ID fourni")
    elif form_state == "create":
        obj = None
    else:
        raise ValueError("Opération introuvable.")
    return render_template(
        OBJECT_COMPLEMENT,
        form=form,
        object_type=object_type,
        form_state=form_state,
        obj=obj
    )


@bp_stock_htmx_search.post("/object/create")
def create_object():
    """Valide et crée un nouvel objet à partir du formulaire global (HTMX)."""
    form = CreateObjectForm()
    if form.validate_on_submit():
        try:
            new_obj_id = save_object_complete(form)
            return render_template(
                OBJECT_FORM,
                form=form,
                form_state="created",
                created_id=new_obj_id,
            )
        except ValueError as exc:
            flash(str(exc), "danger")
            return (
                render_template(
                    OBJECT_FORM,
                    form=form,
                    form_state="create",
                ),
                422,
            )
    return (
        render_template(
            OBJECT_FORM,
            form=form,
            form_state="create",
        ),
        423,
    )


@bp_stock_htmx_search.post("/object/edit/<int:object_id>")
def edit_object(object_id: int):
    """Valide et met à jour un objet existant à partir du formulaire global (HTMX)."""
    obj = get_object_by_id(object_id)
    if obj is None:
        return UNKNOWN_OBJECT, 404
    form = CreateObjectForm()
    if form.validate_on_submit():
        try:
            updated_obj_id = save_object_complete(form, object_id=obj.id)
            return render_template(
                OBJECT_FORM, form=form, form_state="updated", updated_id=updated_obj_id
            )
        except ValueError as exc:
            flash(str(exc), "danger")
            print(f"DEBUG Error updating object: {exc}")
            return (
                render_template(
                    OBJECT_FORM,
                    form=form,
                    form_state="edit",
                    obj=obj,
                ),
                422,
            )
    print(f"DEBUG Form errors: {form.errors}")
    return (
        render_template(
            OBJECT_FORM,
            form=form,
            form_state="edit",
            obj=obj,
        ),
        422,
    )


@bp_stock_htmx_search.get("/object/toggle-active/<int:object_id>")
def object_toggle_active_modal(object_id: int):
    """Retourne la modale de confirmation d'activation/désactivation (HTMX)."""
    obj = get_object_by_id(object_id)
    if obj is None:
        return UNKNOWN_OBJECT, 404
    return render_template(TOGGLE_ACTIVE_MODAL, obj=obj)


@bp_stock_htmx_search.post("/object/toggle-active/<int:object_id>")
def object_toggle_active(object_id: int):
    """Bascule le statut actif/inactif d'un objet (HTMX)."""
    try:
        new_status = toggle_object_active(object_id)
        label = "activé" if new_status else "désactivé"
        return render_template(
            TOGGLE_ACTIVE_MODAL,
            obj=None,
            success=True,
            label=label,
        )
    except ValueError as exc:
        return f"<p class='text-danger'>{exc}</p>", 404


@bp_stock_htmx_search.post("/dilicom/<int:object_id>/add")
def dilicom_add(object_id: int):
    """Planifie l'ajout d'un objet au référentiel Dilicom (HTMX)."""
    gln13 = request.form.get("gln13", "").strip()
    if not gln13:
        return "<p class='text-danger'>GLN13 manquant.</p>", 422
    add_object_to_dilicom(object_id, gln13)
    dilicom_ref, obj = get_dilicom_referencial(object_id)
    resp = make_response(
        render_template(DILICOM_MODAL, obj=obj, dilicom_ref=dilicom_ref)
    )
    resp.headers["HX-Trigger"] = "refreshTable"
    return resp


@bp_stock_htmx_search.post("/dilicom/<int:object_id>/remove")
def dilicom_remove(object_id: int):
    """Planifie la suppression d'un objet du référentiel Dilicom (HTMX)."""
    remove_object_from_dilicom(object_id)
    dilicom_ref, obj = get_dilicom_referencial(object_id)
    resp = make_response(
        render_template(DILICOM_MODAL, obj=obj, dilicom_ref=dilicom_ref)
    )
    resp.headers["HX-Trigger"] = "refreshTable"
    return resp
