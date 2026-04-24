"""Parser ONIX 3.0 pour les fichiers de données livres reçus de Dilicom (fichiers DIF).

Les fichiers DIF (*.zip.rdy.csv) sont des archives ZIP contenant un fichier XML au format
ONIX 3.0. Ce module fournit les dataclasses et fonctions nécessaires pour parser ces fichiers
et exploiter les données produit.

Structure ONIX 3.0 prise en charge :
    - [H]  Header          : émetteur, destinataire, horodatage
    - [P.1] RecordReference / NotificationType
    - [P.2] ProductIdentifier (ISBN-13, EAN, propriétaire, BnF…)
    - [P.3] DescriptiveDetail : forme, mesures, titres, contributeurs,
                                langue, pages, sujets, publics
    - [P.14/P.16] CollateralDetail : description éditeur, visuels / extraits
    - [P.19/P.20] PublishingDetail : marque éditoriale, dates de parution
    - [P.25/P.26] ProductSupply : fournisseur, disponibilité, retours, prix
"""

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Namespace ONIX 3.0 Reference
# ---------------------------------------------------------------------------
ONIX_NS = "http://www.editeur.org/onix/3.0/reference"
_NS = f"{{{ONIX_NS}}}"


# ---------------------------------------------------------------------------
# Helpers internes
# ---------------------------------------------------------------------------

def _t(element: ET.Element, tag: str) -> Optional[str]:
    """Retourne le texte d'un élément fils direct, ou None."""
    el = element.find(f"{_NS}{tag}")
    return el.text.strip() if el is not None and el.text else None


def _find(element: ET.Element, tag: str) -> Optional[ET.Element]:
    """Retourne le premier élément fils correspondant au tag, ou None."""
    return element.find(f"{_NS}{tag}")


def _findall(element: ET.Element, tag: str) -> list[ET.Element]:
    """Retourne tous les éléments fils correspondant au tag."""
    return element.findall(f"{_NS}{tag}")


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class ONIXProductIdentifier:
    """Identifiant d'un produit ONIX — groupe P.2.

    Attributes:
        id_type:      Code du type d'identifiant (ex. 15=ISBN-13, 01=propriétaire,
                      31=identifiant BnF, 35=URL BnF).
        id_type_name: Libellé du type d'identifiant (optionnel, ex. « AVM »).
        id_value:     Valeur de l'identifiant.
    """
    id_type: str
    id_type_name: Optional[str] = None
    id_value: str = ""


@dataclass
class ONIXMeasure:
    """Mesure physique d'un produit — groupe P.3.

    Attributes:
        measure_type: Code du type de mesure (01=hauteur, 02=largeur,
                      03=épaisseur, 08=poids).
        value:        Valeur numérique.
        unit:         Unité (cm, kg, mm…).
    """
    measure_type: str
    value: float = 0.0
    unit: str = ""


@dataclass
class ONIXTitle:
    """Titre d'un produit — groupe P.6.

    Attributes:
        title_type: Code du type de titre (01=titre principal, 05=abrégé,
                    10=libellé caisse).
        text:       Texte du titre.
    """
    title_type: str
    text: str = ""


@dataclass
class ONIXContributor:
    """Contributeur (auteur, illustrateur…) d'un produit — groupe P.7.

    Attributes:
        sequence:   Ordre d'affichage.
        role:       Code du rôle (A01=auteur, A12=illustrateur…).
        first_name: Prénom(s) ou noms avant le nom de famille.
        last_name:  Nom de famille (KeyNames).
    """
    sequence: int = 1
    role: str = ""
    first_name: Optional[str] = None
    last_name: str = ""


@dataclass
class ONIXSubject:
    """Classification thématique d'un produit — groupe P.12.

    Attributes:
        scheme: Identifiant du schéma de classification
                (20=mot-clé libre, 29=code CLIL, 93=Thema…).
        code:   Code sujet (pour les schémas codifiés).
        text:   Libellé sujet (pour les schémas texte libre).
    """
    scheme: str = ""
    code: Optional[str] = None
    text: Optional[str] = None


@dataclass
class ONIXAudience:
    """Public visé par le produit — groupe P.13.

    Attributes:
        code_type:  Type de code public (01=ONIX, 02=propriétaire…).
        code_value: Valeur du code (ex. 1=grand public).
    """
    code_type: str = ""
    code_value: str = ""


@dataclass
class ONIXSupportingResource:
    """Ressource associée au produit (visuels, extraits…) — groupe P.16.

    Attributes:
        content_type:  Type de contenu (01=couverture, 31=4ème couv. PDF…).
        mode:          Mode de la ressource (03=image, 04=application/PDF).
        form:          Forme de livraison (01=téléchargeable…).
        filename:      Nom de fichier suggéré (ResourceVersionFeatureType 04).
        url:           URL de la ressource.
        height:        Hauteur en pixels (ResourceVersionFeatureType 02).
        width:         Largeur en pixels (ResourceVersionFeatureType 03).
        size_bytes:    Taille en octets (ResourceVersionFeatureType 07).
        last_updated:  Date de dernière mise à jour (ContentDateRole 17).
    """
    content_type: str = ""
    mode: str = ""
    form: str = ""
    filename: Optional[str] = None
    url: str = ""
    height: Optional[int] = None
    width: Optional[int] = None
    size_bytes: Optional[int] = None
    last_updated: Optional[str] = None


@dataclass
class ONIXPrice:
    """Prix d'un produit — groupe P.26.

    Attributes:
        price_type:       Code du type de prix (01=HT, 04=TTC fixe…).
        amount:           Montant du prix.
        currency:         Code devise ISO 4217 (ex. EUR).
        tax_type:         Code type de taxe (01=TVA…).
        tax_rate_code:    Code du taux de TVA (R=réduit, S=standard…).
        tax_rate_percent: Taux de TVA en pourcentage.
        taxable_amount:   Montant HT taxable.
        territory_included: Pays/régions où ce prix s'applique.
        territory_excluded: Pays/régions exclus de ce prix.
    """
    price_type: str = ""
    amount: float = 0.0
    currency: str = "EUR"
    tax_type: Optional[str] = None
    tax_rate_code: Optional[str] = None
    tax_rate_percent: Optional[float] = None
    taxable_amount: Optional[float] = None
    territory_included: Optional[str] = None
    territory_excluded: Optional[str] = None


@dataclass
class ONIXSupplier:
    """Fournisseur/Distributeur déclaré dans le ProductSupply — groupe P.26.

    Attributes:
        role:     Code rôle fournisseur (01=éditeur, 02=distributeur exclusif…).
        id_type:  Type d'identifiant (06=GLN…).
        id_value: Valeur de l'identifiant (ex. GLN13).
        name:     Nom du fournisseur.
    """
    role: str = ""
    id_type: Optional[str] = None
    id_value: Optional[str] = None
    name: str = ""


@dataclass
class ONIXImprint:
    """Marque éditoriale — groupe P.19.

    Attributes:
        id_type:  Type d'identifiant de la marque (06=GLN…).
        id_value: Valeur de l'identifiant.
        name:     Nom de la marque éditoriale.
    """
    id_type: Optional[str] = None
    id_value: Optional[str] = None
    name: str = ""


@dataclass
class ONIXProduct:
    """Représentation complète d'un produit issu d'un fichier ONIX 3.0.

    Attributes:
        record_reference:   Référence unique de l'enregistrement (= EAN13).
        notification_type:  Code de mise à jour (03=confirmation d'enregistrement…).
        identifiers:        Liste de tous les identifiants produit.
        composition:        Code composition du produit (00=produit simple…).
        form:               Code présentation du produit (BC=broché…).
        measures:           Mesures physiques (hauteur, largeur, épaisseur, poids).
        titles:             Titres (principal, abrégé, libellé caisse…).
        contributors:       Contributeurs (auteurs, illustrateurs…).
        language_code:      Code langue ISO 639-2 (ex. fre).
        page_count:         Nombre de pages.
        subjects:           Classifications thématiques (CLIL, Thema, mots-clés…).
        audiences:          Publics visés.
        description:        Texte de présentation éditeur (TextType 03).
        resources:          Ressources associées (visuels, extraits PDF…).
        imprint:            Marque éditoriale.
        publication_date:   Date de parution (PublishingDateRole 01).
        end_of_trade_date:  Date de fin de commercialisation (PublishingDateRole 06).
        market_status:      Statut de commercialisation sur le marché.
        supplier:           Fournisseur/distributeur.
        availability_code:  Code disponibilité (20=disponible, 40=épuisé…).
        returns_code_type:  Type de code retour.
        returns_code:       Code conditions de retour.
        supply_date:        Date de mise à disposition (SupplyDateRole 18).
        prices:             Liste des prix (TTC, HT, par territoire…).
    """
    record_reference: str = ""
    notification_type: str = ""

    # [P.2] Identifiants
    identifiers: list[ONIXProductIdentifier] = field(default_factory=list)

    # [P.3] DescriptiveDetail
    composition: str = ""
    form: str = ""
    measures: list[ONIXMeasure] = field(default_factory=list)
    titles: list[ONIXTitle] = field(default_factory=list)
    contributors: list[ONIXContributor] = field(default_factory=list)
    language_code: Optional[str] = None
    page_count: Optional[int] = None
    subjects: list[ONIXSubject] = field(default_factory=list)
    audiences: list[ONIXAudience] = field(default_factory=list)

    # [P.14/P.16] CollateralDetail
    description: Optional[str] = None
    resources: list[ONIXSupportingResource] = field(default_factory=list)

    # [P.19/P.20] PublishingDetail
    imprint: Optional[ONIXImprint] = None
    publication_date: Optional[str] = None
    end_of_trade_date: Optional[str] = None

    # [P.25/P.26] ProductSupply
    market_status: Optional[str] = None
    supplier: Optional[ONIXSupplier] = None
    availability_code: Optional[str] = None
    returns_code_type: Optional[str] = None
    returns_code: Optional[str] = None
    supply_date: Optional[str] = None
    prices: list[ONIXPrice] = field(default_factory=list)

    # ------------------------------------------------------------------ #
    # Propriétés utilitaires
    # ------------------------------------------------------------------ #

    @property
    def isbn13(self) -> Optional[str]:
        """Retourne l'ISBN-13 du produit (ProductIDType 15), ou None."""
        for ident in self.identifiers:
            if ident.id_type == "15":
                return ident.id_value
        return None

    @property
    def ean13(self) -> Optional[str]:
        """Alias de isbn13 — l'EAN-13 est identique à l'ISBN-13."""
        return self.isbn13

    @property
    def main_title(self) -> Optional[str]:
        """Retourne le titre principal (TitleType 01), ou None."""
        for t in self.titles:
            if t.title_type == "01":
                return t.text
        return self.titles[0].text if self.titles else None

    @property
    def authors(self) -> list[ONIXContributor]:
        """Retourne les auteurs principaux (ContributorRole A01)."""
        return [c for c in self.contributors if c.role == "A01"]

    @property
    def cover_url(self) -> Optional[str]:
        """Retourne l'URL de la couverture pleine résolution (si disponible)."""
        for r in self.resources:
            if r.content_type == "01" and r.mode == "03":
                if r.filename and "full" in (r.filename or ""):
                    return r.url
        for r in self.resources:
            if r.content_type == "01" and r.mode == "03":
                return r.url
        return None

    @property
    def price_ttc_fr(self) -> Optional[float]:
        """Retourne le prix TTC France (PriceType 04, CountriesIncluded FR)."""
        for p in self.prices:
            if p.price_type == "04" and p.territory_included == "FR":
                return p.amount
        return None


@dataclass
class ONIXMessage:
    """Message ONIX complet — un fichier DIF correspond à un ONIXMessage.

    Attributes:
        sender_name:    Nom de l'émetteur (ex. « DILICOM »).
        sender_gln:     GLN de l'émetteur.
        addressee_name: Nom du destinataire (ex. nom de la librairie).
        addressee_gln:  GLN du destinataire.
        message_number: Numéro du message (= numéro du fichier DIF).
        sent_datetime:  Horodatage d'envoi (format YYYYMMDDTHHMMSSZ).
        products:       Liste des produits contenus dans le message.
    """
    sender_name: str = ""
    sender_gln: Optional[str] = None
    addressee_name: str = ""
    addressee_gln: Optional[str] = None
    message_number: str = ""
    sent_datetime: str = ""
    products: list[ONIXProduct] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Fonctions de parsing internes
# ---------------------------------------------------------------------------

def _parse_identifiers(product_el: ET.Element) -> list[ONIXProductIdentifier]:
    result = []
    for pi in _findall(product_el, "ProductIdentifier"):
        result.append(ONIXProductIdentifier(
            id_type=_t(pi, "ProductIDType") or "",
            id_type_name=_t(pi, "IDTypeName"),
            id_value=_t(pi, "IDValue") or "",
        ))
    return result


def _parse_descriptive_detail(dd: ET.Element) -> dict:
    data: dict = {
        "composition": _t(dd, "ProductComposition") or "",
        "form": _t(dd, "ProductForm") or "",
        "measures": [],
        "titles": [],
        "contributors": [],
        "language_code": None,
        "page_count": None,
        "subjects": [],
        "audiences": [],
    }

    # Mesures physiques
    for m in _findall(dd, "Measure"):
        try:
            val = float(_t(m, "Measurement") or "0")
        except ValueError:
            val = 0.0
        data["measures"].append(ONIXMeasure(
            measure_type=_t(m, "MeasureType") or "",
            value=val,
            unit=_t(m, "MeasureUnitCode") or "",
        ))

    # Titres (tous types)
    for td in _findall(dd, "TitleDetail"):
        title_type = _t(td, "TitleType") or ""
        for te in _findall(td, "TitleElement"):
            text = _t(te, "TitleText") or ""
            if text:
                data["titles"].append(ONIXTitle(title_type=title_type, text=text))

    # Contributeurs
    for c in _findall(dd, "Contributor"):
        try:
            seq = int(_t(c, "SequenceNumber") or "1")
        except ValueError:
            seq = 1
        data["contributors"].append(ONIXContributor(
            sequence=seq,
            role=_t(c, "ContributorRole") or "",
            first_name=_t(c, "NamesBeforeKey"),
            last_name=_t(c, "KeyNames") or "",
        ))

    # Langue
    lang_el = _find(dd, "Language")
    if lang_el is not None:
        data["language_code"] = _t(lang_el, "LanguageCode")

    # Nombre de pages (ExtentType 00)
    for ext in _findall(dd, "Extent"):
        if _t(ext, "ExtentType") == "00":
            try:
                data["page_count"] = int(_t(ext, "ExtentValue") or "0")
            except ValueError:
                data["page_count"] = None
            break

    # Classifications thématiques
    for s in _findall(dd, "Subject"):
        data["subjects"].append(ONIXSubject(
            scheme=_t(s, "SubjectSchemeIdentifier") or "",
            code=_t(s, "SubjectCode"),
            text=_t(s, "SubjectHeadingText"),
        ))

    # Publics visés
    for a in _findall(dd, "Audience"):
        data["audiences"].append(ONIXAudience(
            code_type=_t(a, "AudienceCodeType") or "",
            code_value=_t(a, "AudienceCodeValue") or "",
        ))

    return data


def _parse_collateral_detail(cd: ET.Element) -> dict:
    data: dict = {"description": None, "resources": []}

    # Texte de présentation éditeur (TextType 03)
    for tc in _findall(cd, "TextContent"):
        if _t(tc, "TextType") == "03":
            data["description"] = _t(tc, "Text")
            break

    # Ressources associées (visuels, extraits PDF…)
    for sr in _findall(cd, "SupportingResource"):
        rv_el = _find(sr, "ResourceVersion")
        if rv_el is None:
            continue

        filename: Optional[str] = None
        height: Optional[int] = None
        width: Optional[int] = None
        size_bytes: Optional[int] = None

        for feat in _findall(rv_el, "ResourceVersionFeature"):
            feat_type = _t(feat, "ResourceVersionFeatureType")
            feat_val = _t(feat, "FeatureValue")
            if feat_type == "04":
                filename = feat_val
            elif feat_type == "02":
                try:
                    height = int(feat_val or "0")
                except ValueError:
                    pass
            elif feat_type == "03":
                try:
                    width = int(feat_val or "0")
                except ValueError:
                    pass
            elif feat_type == "07":
                try:
                    size_bytes = int(feat_val or "0")
                except ValueError:
                    pass

        last_updated: Optional[str] = None
        cd_el = _find(rv_el, "ContentDate")
        if cd_el is not None:
            last_updated = _t(cd_el, "Date")

        data["resources"].append(ONIXSupportingResource(
            content_type=_t(sr, "ResourceContentType") or "",
            mode=_t(sr, "ResourceMode") or "",
            form=_t(rv_el, "ResourceForm") or "",
            filename=filename,
            url=_t(rv_el, "ResourceLink") or "",
            height=height,
            width=width,
            size_bytes=size_bytes,
            last_updated=last_updated,
        ))

    return data


def _parse_publishing_detail(pd_el: ET.Element) -> dict:
    data: dict = {"imprint": None, "publication_date": None, "end_of_trade_date": None}

    imp_el = _find(pd_el, "Imprint")
    if imp_el is not None:
        imp_id_el = _find(imp_el, "ImprintIdentifier")
        data["imprint"] = ONIXImprint(
            id_type=_t(imp_id_el, "ImprintIDType") if imp_id_el is not None else None,
            id_value=_t(imp_id_el, "IDValue") if imp_id_el is not None else None,
            name=_t(imp_el, "ImprintName") or "",
        )

    for pub_date in _findall(pd_el, "PublishingDate"):
        role = _t(pub_date, "PublishingDateRole")
        date_val = _t(pub_date, "Date")
        if role == "01":
            data["publication_date"] = date_val
        elif role == "06":
            data["end_of_trade_date"] = date_val

    return data


def _parse_product_supply(ps_el: ET.Element) -> dict:
    data: dict = {
        "market_status": None,
        "supplier": None,
        "availability_code": None,
        "returns_code_type": None,
        "returns_code": None,
        "supply_date": None,
        "prices": [],
    }

    mpd_el = _find(ps_el, "MarketPublishingDetail")
    if mpd_el is not None:
        data["market_status"] = _t(mpd_el, "MarketPublishingStatus")

    sd_el = _find(ps_el, "SupplyDetail")
    if sd_el is None:
        return data

    # Fournisseur/Distributeur
    sup_el = _find(sd_el, "Supplier")
    if sup_el is not None:
        sup_id_el = _find(sup_el, "SupplierIdentifier")
        data["supplier"] = ONIXSupplier(
            role=_t(sup_el, "SupplierRole") or "",
            id_type=_t(sup_id_el, "SupplierIDType") if sup_id_el is not None else None,
            id_value=_t(sup_id_el, "IDValue") if sup_id_el is not None else None,
            name=_t(sup_el, "SupplierName") or "",
        )

    # Disponibilité
    data["availability_code"] = _t(sd_el, "ProductAvailability")

    # Conditions de retour
    rc_el = _find(sd_el, "ReturnsConditions")
    if rc_el is not None:
        data["returns_code_type"] = _t(rc_el, "ReturnsCodeType")
        data["returns_code"] = _t(rc_el, "ReturnsCode")

    # Date d'approvisionnement (SupplyDateRole 18)
    for sup_date in _findall(sd_el, "SupplyDate"):
        if _t(sup_date, "SupplyDateRole") == "18":
            data["supply_date"] = _t(sup_date, "Date")
            break

    # Prix
    for pr_el in _findall(sd_el, "Price"):
        try:
            amount = float(_t(pr_el, "PriceAmount") or "0")
        except ValueError:
            amount = 0.0

        tax_type = tax_rate_code = None
        tax_rate: Optional[float] = None
        taxable_amount: Optional[float] = None
        tax_el = _find(pr_el, "Tax")
        if tax_el is not None:
            tax_type = _t(tax_el, "TaxType")
            tax_rate_code = _t(tax_el, "TaxRateCode")
            try:
                tax_rate = float(_t(tax_el, "TaxRatePercent") or "0")
                taxable_amount = float(_t(tax_el, "TaxableAmount") or "0")
            except ValueError:
                pass

        territory_included = territory_excluded = None
        terr_el = _find(pr_el, "Territory")
        if terr_el is not None:
            territory_included = (
                _t(terr_el, "CountriesIncluded") or _t(terr_el, "RegionsIncluded")
            )
            territory_excluded = _t(terr_el, "CountriesExcluded")

        data["prices"].append(ONIXPrice(
            price_type=_t(pr_el, "PriceType") or "",
            amount=amount,
            currency=_t(pr_el, "CurrencyCode") or "EUR",
            tax_type=tax_type,
            tax_rate_code=tax_rate_code,
            tax_rate_percent=tax_rate,
            taxable_amount=taxable_amount,
            territory_included=territory_included,
            territory_excluded=territory_excluded,
        ))

    return data


def _parse_product(product_el: ET.Element) -> ONIXProduct:
    """Parse un élément <Product> ONIX 3.0 en un objet ONIXProduct."""
    p = ONIXProduct(
        record_reference=_t(product_el, "RecordReference") or "",
        notification_type=_t(product_el, "NotificationType") or "",
        identifiers=_parse_identifiers(product_el),
    )

    dd_el = _find(product_el, "DescriptiveDetail")
    if dd_el is not None:
        dd = _parse_descriptive_detail(dd_el)
        p.composition = dd["composition"]
        p.form = dd["form"]
        p.measures = dd["measures"]
        p.titles = dd["titles"]
        p.contributors = dd["contributors"]
        p.language_code = dd["language_code"]
        p.page_count = dd["page_count"]
        p.subjects = dd["subjects"]
        p.audiences = dd["audiences"]

    cd_el = _find(product_el, "CollateralDetail")
    if cd_el is not None:
        cd = _parse_collateral_detail(cd_el)
        p.description = cd["description"]
        p.resources = cd["resources"]

    pd_el = _find(product_el, "PublishingDetail")
    if pd_el is not None:
        pd = _parse_publishing_detail(pd_el)
        p.imprint = pd["imprint"]
        p.publication_date = pd["publication_date"]
        p.end_of_trade_date = pd["end_of_trade_date"]

    # On prend le premier ProductSupply (le marché principal)
    ps_el = _find(product_el, "ProductSupply")
    if ps_el is not None:
        ps = _parse_product_supply(ps_el)
        p.market_status = ps["market_status"]
        p.supplier = ps["supplier"]
        p.availability_code = ps["availability_code"]
        p.returns_code_type = ps["returns_code_type"]
        p.returns_code = ps["returns_code"]
        p.supply_date = ps["supply_date"]
        p.prices = ps["prices"]

    return p


# ---------------------------------------------------------------------------
# API publique
# ---------------------------------------------------------------------------

def parse_onix_file(path: str | Path) -> ONIXMessage:
    """Parse un fichier ONIX 3.0 XML et retourne un objet ONIXMessage.

    :param path: Chemin vers le fichier XML ONIX 3.0 (obtenu après décompression
                 du fichier DIF*.zip.rdy.csv reçu de Dilicom).
    :return: Un ONIXMessage contenant le header et la liste des produits parsés.
    :raises ET.ParseError: Si le fichier XML est malformé.
    :raises FileNotFoundError: Si le fichier n'existe pas.

    Example::

        from app_back.v1.dilicom.onix_parser import parse_onix_file

        msg = parse_onix_file("489084922.xml")
        for product in msg.products:
            print(product.isbn13, product.main_title, product.price_ttc_fr)
    """
    tree = ET.parse(str(path))
    return parse_onix_element(tree.getroot())


def parse_onix_element(root: ET.Element) -> ONIXMessage:
    """Parse un élément racine <ONIXMessage> et retourne un objet ONIXMessage.

    Utile quand le XML est déjà chargé en mémoire (ex. depuis un ZIP en mémoire).

    :param root: Élément racine de l'arbre XML ONIX 3.0.
    :return: Un ONIXMessage contenant le header et la liste des produits parsés.
    """
    msg = ONIXMessage()

    header = _find(root, "Header")
    if header is not None:
        sender = _find(header, "Sender")
        if sender is not None:
            msg.sender_name = _t(sender, "SenderName") or ""
            sender_id = _find(sender, "SenderIdentifier")
            if sender_id is not None:
                msg.sender_gln = _t(sender_id, "IDValue")

        addressee = _find(header, "Addressee")
        if addressee is not None:
            msg.addressee_name = _t(addressee, "AddresseeName") or ""
            addr_id = _find(addressee, "AddresseeIdentifier")
            if addr_id is not None:
                msg.addressee_gln = _t(addr_id, "IDValue")

        msg.message_number = _t(header, "MessageNumber") or ""
        msg.sent_datetime = _t(header, "SentDateTime") or ""

    for product_el in _findall(root, "Product"):
        msg.products.append(_parse_product(product_el))

    return msg
