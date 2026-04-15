"""
Module de définition des structures de données pour les fichiers distributeurs reçus de Dilicom.
"""

from typing import Optional, List, Tuple, Any
from dataclasses import dataclass, fields
import pandas as pd

@dataclass
class FileDistri:
    """
    Structure de données pour représenter un fichier de type distributeur reçu de Dilicom.
    Attributs:
    - header: Liste de chaînes représentant les champs d'en-tête du fichier.
    - footer: Chaîne représentant le champ de pied de page du fichier.
    - data: DataFrame contenant les données du fichier, avec les champs organisés en colonnes.
    """
    header: List[str]
    footer: str
    data: 'pd.DataFrame'  # type: ignore

@dataclass
class DistributorDataBloc1:
    """
    Structure de données pour les fichiers de type 'distributeur.
    Attributs:
    - ref: Numéro de la ligne
    - mvt: Type de mouvement
        - 00: Extraction complète
        - 01: Extraction des distributeurs qui peuvent faire l'objet de commandes via DILICOM
        - 03 = Création
        - 04 = Modification complète
        - 05 = Modification du bloc 1
        - 06 = Modification du bloc 2
        - 07 = Modification du bloc 3
        - 08 = Suppression
    - gln: Code GLN du distributeur
    - rs1: Raison sociale 1
    - rs2: Raison sociale 2 (optionnel)
    - numero_voie: Numéro de voie (optionnel)
    - adresse_l1: Adresse ligne 1 (optionnel)
    - adresse_l2: Adresse ligne 2 (optionnel)
    - adresse_l3: Adresse ligne 3 (optionnel)
    - code_postal: Code postal (optionnel)
    - ville: Ville
    - pays: Pays
    - rejet_postal: Rejet postal (optionnel)
    - num_tel: Numéro de téléphone (optionnel)
    - num_fax: Numéro de fax (optionnel)
    - email: Adresse email (optionnel)
    - website: Site web (optionnel)
    - siren_or_siret: Numéro SIREN ou SIRET (optionnel)
    - num_tva_intracom: Numéro de TVA intracommunautaire (optionnel)
    - gln_repreneur: Code GLN du repreneur (optionnel)
    - rs_repreneur: Raison sociale du repreneur (optionnel)
    - fonction: Fonction du contact
        - 01 = Distributeur
        - 02 = Grossiste/Comptoir/GIE
    - adherent_prisme: Indicateur d'adhésion au PRISME
        - 0 = Non adhérent
        - 1 = Adhérent
    """
    ref: str
    mvt: str
    gln: str
    rs1: str
    rs2: Optional[str]
    numero_voie: Optional[str]
    adresse_l1: Optional[str]
    adresse_l2: Optional[str]
    adresse_l3: Optional[str]
    code_postal: Optional[str]
    ville: str
    pays: str
    rejet_postal: Optional[str]
    num_tel: Optional[str]
    num_fax: Optional[str]
    email: Optional[str]
    website: Optional[str]
    siren_or_siret: Optional[str]
    num_tva_intracom: Optional[str]
    gln_repreneur: Optional[str]
    rs_repreneur: Optional[str]
    fonction: str
    adherent_prisme: int


@dataclass
class DistributorDataBloc2:
    """
    Structure de données pour les fichiers de type distributeur,
    bloc 2, connexion au serveur Dilicom.
    Attributs:
    - integration_commande: Intégration des commandes
        - 01 = Automatique
        - 02 = Manuelle
        - 03 = Semi-automatique
        - 00 ou 04 = Non précisé
    - place_commande: Place de commande
        - 00 = Non précisé
        - 01 = prioritaire
        - 02 = non-prioritaire
    - heure_limite:
        - HHMM: Heure limite de prise en compte des commandes pour le jour même
    - jours_collecte: Jours de collecte des commandes
        - LMMJVSD, O si non et 1 si oui
    - format_commandes: Format des commandes
        - 01 = Imprimable
        - 02 = EDI (Codifié et intégrable)
    - type_connection: Type de connexion
        - 01 = Fax/Mail/Téléchargement
        - 02 = EDI (Codifié et intégrable)
    - avis_expedition: Génération des avis d'expédition
        - 01 = Pré-facturation/Stock théorique
        - 02 = Post-facturation/Fermeture du camion
    """
    integration_commande: str
    place_commande: str
    heure_limite: Optional[str]
    jours_collecte: Optional[str]
    format_commandes: Optional[str]
    type_connection: Optional[str]
    avis_expedition: Optional[str]


@dataclass
class DistributorDataBloc3:
    """
    Structure de données pour les fichiers de type distributeur,
    bloc 3, informations complémentaires.
        - 0 = Non
        - 1 = Oui
    Attributs:
    - fiche_produit
    - propo_commandes
    - commande
    - reponse_commandes
    - avis_exp_v1
    - avis_exp_v2
    - journal_mvt
    - reclamation
    - retour_dde_autorisation
    - retour_accord_fournisseur
    - retour_avis
    - facture_electronique
    - demat_facture_fiscale
    - centralisation_paiements
    """
    fiche_produit: Optional[int]
    propo_commandes: Optional[int]
    commande: Optional[int]
    reponse_commandes: Optional[int]
    avis_exp_v1: Optional[int]
    avis_exp_v2: Optional[int]
    journal_mvt: Optional[int]
    reclamation: Optional[int]
    retour_dde_autorisation: Optional[int]
    retour_accord_fournisseur: Optional[int]
    retour_avis: Optional[int]
    facture_electronique: Optional[int]
    demat_facture_fiscale: Optional[int]
    centralisation_paiements: Optional[int]


@dataclass
class DistributorLineData:
    """
    Structure de données pour une ligne de fichier de type distributeur,
    regroupant les blocs 1, 2 et 3.
    """
    bloc1: DistributorDataBloc1
    bloc2: DistributorDataBloc2
    bloc3: DistributorDataBloc3
    fin_ligne: str


@dataclass
class DistributorData:
    """
    Structure de données complète pour les fichiers de type distributeur,
    regroupant les blocs 1, 2 et 3.
    """
    debut_fichier: str
    ref_edi: str
    date_edi: int
    lines: List[DistributorLineData]
    fin_fichier: str


def _row_to_dataclass_by_position(row: pd.Series[Any] | List[Any], cls: Any) -> Any:
    """
    Convertit une ligne de données en une instance d'une dataclass en utilisant
    la position des champs.

    Args:
        row: La ligne de données à convertir (pandas Series ou liste).
        cls: La classe de dataclass dans laquelle convertir la ligne.
    Returns:
        Une instance de la dataclass cls avec les valeurs de la ligne.
    """
    values = list(row)  # valeurs dans l'ordre du DataFrame
    attrs = [f.name for f in fields(cls)]  # attributs dans l'ordre de la dataclass
    kwargs = dict(zip(attrs, values))
    return cls(**kwargs)


def _split_row_for_dataclasses(
        row: pd.Series[Any] | List[Any]
        ) -> Tuple[DistributorDataBloc1, DistributorDataBloc2, DistributorDataBloc3]:
    """
    Divise une ligne de données en segments correspondant à plusieurs dataclasses
    en utilisant la position des champs.
    Args:
        row: La ligne de données à diviser (pandas Series ou liste).
    Returns:
        Un tuple d'instances de dataclass correspondant aux segments de la ligne.
    """
    classes = DistributorDataBloc1, DistributorDataBloc2, DistributorDataBloc3
    pos = 0
    result: List[Any] = []
    for cls in classes:
        n = len(fields(cls))
        if isinstance(row, pd.Series):
            segment: pd.Series[Any] | List[Any] = row.iloc[pos:pos+n]
        else:
            segment = row[pos:pos+n]
        result.append(_row_to_dataclass_by_position(segment, cls))
        pos += n
    return result[0], result[1], result[2]


def df_to_distributor_data(distri_file: FileDistri) -> DistributorData:
    """
    Convertit un DataFrame en une instance de DistributorData en utilisant la position des champs.

    Args:
        distri_file: Le FileDistri à convertir.
    Returns:
        Une instance de DistributorData avec les données du DataFrame.
    """
    lines: List[DistributorLineData] = []
    header, footer, df = distri_file.header, distri_file.footer, distri_file.data

    for _, row in df.iterrows():
        blocs = _split_row_for_dataclasses(row)

        if len(blocs) != 3:
            message = f"""
            3 blocs attendus pour chaque ligne, mais {len(blocs)} ont été trouvés.
            Vérifiez la structure du DataFrame et les dataclasses.
            """
            raise ValueError(message)
        line = DistributorLineData(
            bloc1=blocs[0],
            bloc2=blocs[1],
            bloc3=blocs[2],
            fin_ligne=row.iloc[-1]  # dernière colonne
        )

        lines.append(line)

    head_filed = header[0] if len(header) > 0 else ""
    ref_filed = header[1] if len(header) > 1 else ""
    date_filed = int(header[2]) if len(header) > 2 and header[2].isdigit() else 0

    return DistributorData(
        debut_fichier=head_filed,
        ref_edi=ref_filed,
        date_edi=date_filed,
        lines=lines,
        fin_fichier=footer
    )
